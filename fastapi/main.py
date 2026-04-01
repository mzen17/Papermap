from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import SQLModel, Field, Session, create_engine, select, or_
from sqlalchemy import text
from typing import Optional, List
from pathlib import Path
import hashlib
import hmac
import secrets
import os
import json

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./papermap.db")
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Papermap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

SESSION_COOKIE = "pm_session"
_API_PREFIXES = (
    "/workdirs", "/projects", "/mindmaps", "/objects",
    "/positions", "/notes", "/relationships", "/me",
)


# ─── Password helpers ─────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"{salt}:{dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, dk_hex = stored.split(":", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return hmac.compare_digest(dk.hex(), dk_hex)


# ─── Auth middleware ───────────────────────────────────────────────────────────

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS":
        return await call_next(request)
    if path.startswith("/auth/"):
        return await call_next(request)
    if not any(path == p or path.startswith(p + "/") for p in _API_PREFIXES):
        return await call_next(request)

    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with Session(engine) as s:
            sess = s.exec(select(UserSession).where(UserSession.token == token)).first()
            if sess:
                request.state.user_id = sess.user_id
                return await call_next(request)

    return JSONResponse({"detail": "Unauthorized"}, status_code=401)


def _current_user_id(request: Request) -> int:
    uid = getattr(request.state, "user_id", None)
    if uid is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return uid


# ─── Table Models ─────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str


class UserSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    user_id: int = Field(foreign_key="user.id")


class Workdir(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    workdir_id: int = Field(foreign_key="workdir.id")


class MindMap(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    project_id: int = Field(foreign_key="project.id")


class MapObject(SQLModel, table=True):
    __tablename__ = "mapobject"
    id: Optional[int] = Field(default=None, primary_key=True)
    mindmap_id: int = Field(foreign_key="mindmap.id")
    type: str  # "paper" | "text"
    title: Optional[str] = None
    link: Optional[str] = None
    tags: Optional[str] = None  # JSON array string
    text: Optional[str] = None


class CanvasPosition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mindmap_id: int = Field(foreign_key="mindmap.id")
    object_id: int = Field(foreign_key="mapobject.id")
    x: float = 0.0
    y: float = 0.0


class Note(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    object_id: int = Field(foreign_key="mapobject.id")
    content: str = ""


class ObjRelationship(SQLModel, table=True):
    __tablename__ = "objrelationship"
    id: Optional[int] = Field(default=None, primary_key=True)
    mindmap_id: int = Field(foreign_key="mindmap.id")
    obj1_id: int = Field(foreign_key="mapobject.id")
    obj2_id: int = Field(foreign_key="mapobject.id")
    description: Optional[str] = None


# ─── Request/Response Schemas ─────────────────────────────────────────────────

class UserCreate(SQLModel):
    username: str
    password: str


class UserOut(SQLModel):
    id: int
    username: str


class WorkdirCreate(SQLModel):
    name: str


class WorkdirUpdate(SQLModel):
    name: str


class ProjectCreate(SQLModel):
    name: str
    workdir_id: int


class ProjectUpdate(SQLModel):
    name: str


class MindMapCreate(SQLModel):
    name: str
    project_id: int


class MapObjectCreate(SQLModel):
    mindmap_id: int
    type: str
    title: Optional[str] = None
    link: Optional[str] = None
    tags: Optional[List[str]] = None
    text: Optional[str] = None
    x: float = 200.0
    y: float = 200.0


class MapObjectUpdate(SQLModel):
    title: Optional[str] = None
    link: Optional[str] = None
    tags: Optional[List[str]] = None
    text: Optional[str] = None


class PositionUpdate(SQLModel):
    x: float
    y: float


class NoteCreate(SQLModel):
    content: str = ""


class RelationshipCreate(SQLModel):
    mindmap_id: int
    obj1_id: int
    obj2_id: int
    description: Optional[str] = None


class RelationshipUpdate(SQLModel):
    description: Optional[str] = None


# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    # Migrate: add user_id column to workdir table if it doesn't exist yet
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE workdir ADD COLUMN user_id INTEGER REFERENCES user(id)"))
            conn.commit()
        except Exception:
            pass  # column already exists


# ─── Ownership helpers ────────────────────────────────────────────────────────

def _require_workdir(s: Session, workdir_id: int, user_id: int) -> Workdir:
    w = s.get(Workdir, workdir_id)
    if not w:
        raise HTTPException(404)
    if w.user_id != user_id:
        raise HTTPException(403)
    return w


def _require_project(s: Session, project_id: int, user_id: int) -> Project:
    p = s.get(Project, project_id)
    if not p:
        raise HTTPException(404)
    _require_workdir(s, p.workdir_id, user_id)
    return p


def _require_mindmap(s: Session, mindmap_id: int, user_id: int) -> MindMap:
    mm = s.get(MindMap, mindmap_id)
    if not mm:
        raise HTTPException(404)
    _require_project(s, mm.project_id, user_id)
    return mm


def _require_object(s: Session, obj_id: int, user_id: int) -> MapObject:
    obj = s.get(MapObject, obj_id)
    if not obj:
        raise HTTPException(404)
    _require_mindmap(s, obj.mindmap_id, user_id)
    return obj


# ─── Cascade Helpers ──────────────────────────────────────────────────────────

def _cascade_delete_mindmap(s: Session, mid: int):
    mm = s.get(MindMap, mid)
    if not mm:
        return
    objs = s.exec(select(MapObject).where(MapObject.mindmap_id == mid)).all()
    obj_ids = [o.id for o in objs]
    if obj_ids:
        for n in s.exec(select(Note).where(Note.object_id.in_(obj_ids))).all():
            s.delete(n)
    for r in s.exec(select(ObjRelationship).where(ObjRelationship.mindmap_id == mid)).all():
        s.delete(r)
    for pos in s.exec(select(CanvasPosition).where(CanvasPosition.mindmap_id == mid)).all():
        s.delete(pos)
    for o in objs:
        s.delete(o)
    s.delete(mm)


def _cascade_delete_project(s: Session, pid: int):
    p = s.get(Project, pid)
    if not p:
        return
    for mm in s.exec(select(MindMap).where(MindMap.project_id == pid)).all():
        _cascade_delete_mindmap(s, mm.id)
    s.delete(p)


# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.post("/auth/register")
def register(data: UserCreate):
    username = data.username.strip()
    if not username or not data.password:
        raise HTTPException(400, "Username and password are required.")
    with Session(engine) as s:
        if s.exec(select(User).where(User.username == username)).first():
            raise HTTPException(409, "Username already taken.")
        user = User(username=username, password_hash=_hash_password(data.password))
        s.add(user)
        s.commit()
        s.refresh(user)
        user_id, user_name = user.id, user.username
        token = secrets.token_hex(32)
        s.add(UserSession(token=token, user_id=user_id))
        s.commit()
    response = JSONResponse({"id": user_id, "username": user_name})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=30 * 24 * 3600)
    return response


@app.post("/auth/login")
def login(data: UserCreate):
    with Session(engine) as s:
        user = s.exec(select(User).where(User.username == data.username.strip())).first()
        if not user or not _verify_password(data.password, user.password_hash):
            raise HTTPException(401, "Invalid username or password.")
        user_id, user_name = user.id, user.username
        token = secrets.token_hex(32)
        s.add(UserSession(token=token, user_id=user_id))
        s.commit()
    response = JSONResponse({"id": user_id, "username": user_name})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=30 * 24 * 3600)
    return response


@app.post("/auth/logout")
def logout(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with Session(engine) as s:
            sess = s.exec(select(UserSession).where(UserSession.token == token)).first()
            if sess:
                s.delete(sess)
                s.commit()
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/me")
def me(request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        user = s.get(User, uid)
        if not user:
            raise HTTPException(404)
        return {"id": user.id, "username": user.username}


# ─── Workdirs ─────────────────────────────────────────────────────────────────

@app.get("/workdirs", response_model=List[Workdir])
def list_workdirs(request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        return s.exec(select(Workdir).where(Workdir.user_id == uid)).all()


@app.post("/workdirs", response_model=Workdir)
def create_workdir(data: WorkdirCreate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        w = Workdir(name=data.name, user_id=uid)
        s.add(w)
        s.commit()
        s.refresh(w)
        return w


@app.patch("/workdirs/{id}", response_model=Workdir)
def rename_workdir(id: int, data: WorkdirUpdate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        w = _require_workdir(s, id, uid)
        w.name = data.name
        s.add(w)
        s.commit()
        s.refresh(w)
        return w


@app.delete("/workdirs/{id}")
def delete_workdir(id: int, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        w = _require_workdir(s, id, uid)
        for p in s.exec(select(Project).where(Project.workdir_id == id)).all():
            _cascade_delete_project(s, p.id)
        s.delete(w)
        s.commit()
        return {"ok": True}


# ─── Projects ─────────────────────────────────────────────────────────────────

@app.get("/workdirs/{workdir_id}/projects", response_model=List[Project])
def list_projects(workdir_id: int, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        _require_workdir(s, workdir_id, uid)
        return s.exec(select(Project).where(Project.workdir_id == workdir_id)).all()


@app.post("/projects", response_model=Project)
def create_project(data: ProjectCreate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        _require_workdir(s, data.workdir_id, uid)
        p = Project(name=data.name, workdir_id=data.workdir_id)
        s.add(p)
        s.commit()
        s.refresh(p)
        return p


@app.patch("/projects/{id}", response_model=Project)
def rename_project(id: int, data: ProjectUpdate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        p = _require_project(s, id, uid)
        p.name = data.name
        s.add(p)
        s.commit()
        s.refresh(p)
        return p


@app.delete("/projects/{id}")
def delete_project(id: int, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        _require_project(s, id, uid)
        _cascade_delete_project(s, id)
        s.commit()
        return {"ok": True}


# ─── MindMaps ─────────────────────────────────────────────────────────────────

@app.get("/projects/{project_id}/mindmaps", response_model=List[MindMap])
def list_mindmaps(project_id: int, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        _require_project(s, project_id, uid)
        return s.exec(select(MindMap).where(MindMap.project_id == project_id)).all()


@app.post("/mindmaps", response_model=MindMap)
def create_mindmap(data: MindMapCreate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        _require_project(s, data.project_id, uid)
        mm = MindMap(name=data.name, project_id=data.project_id)
        s.add(mm)
        s.commit()
        s.refresh(mm)
        return mm


@app.delete("/mindmaps/{id}")
def delete_mindmap(id: int, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        _require_mindmap(s, id, uid)
        _cascade_delete_mindmap(s, id)
        s.commit()
        return {"ok": True}


@app.get("/mindmaps/{id}/full")
def get_mindmap_full(id: int, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        mm = _require_mindmap(s, id, uid)
        objects = s.exec(select(MapObject).where(MapObject.mindmap_id == id)).all()
        positions = {
            p.object_id: p
            for p in s.exec(select(CanvasPosition).where(CanvasPosition.mindmap_id == id)).all()
        }
        relationships = s.exec(
            select(ObjRelationship).where(ObjRelationship.mindmap_id == id)
        ).all()

        note_counts = {}
        for n in s.exec(
            select(Note).where(Note.object_id.in_([o.id for o in objects]))
        ).all():
            note_counts[n.object_id] = note_counts.get(n.object_id, 0) + 1

        objs_out = []
        for obj in objects:
            o = obj.model_dump()
            o["tags"] = json.loads(obj.tags) if obj.tags else []
            pos = positions.get(obj.id)
            o["x"] = pos.x if pos else 100.0
            o["y"] = pos.y if pos else 100.0
            o["pos_id"] = pos.id if pos else None
            o["note_count"] = note_counts.get(obj.id, 0)
            objs_out.append(o)

        return {
            "mindmap": mm.model_dump(),
            "objects": objs_out,
            "relationships": [r.model_dump() for r in relationships],
        }


# ─── Objects ──────────────────────────────────────────────────────────────────

@app.post("/objects")
def create_object(data: MapObjectCreate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        _require_mindmap(s, data.mindmap_id, uid)
        obj = MapObject(
            mindmap_id=data.mindmap_id,
            type=data.type,
            title=data.title,
            link=data.link,
            tags=json.dumps(data.tags or []),
            text=data.text,
        )
        s.add(obj)
        s.commit()
        s.refresh(obj)
        pos = CanvasPosition(
            mindmap_id=data.mindmap_id,
            object_id=obj.id,
            x=data.x,
            y=data.y,
        )
        s.add(pos)
        s.commit()
        s.refresh(pos)
        s.refresh(obj)
        result = obj.model_dump()
        result["tags"] = data.tags or []
        result["x"] = pos.x
        result["y"] = pos.y
        result["pos_id"] = pos.id
        return result


@app.patch("/objects/{id}")
def update_object(id: int, data: MapObjectUpdate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        obj = _require_object(s, id, uid)
        if data.title is not None:
            obj.title = data.title
        if data.link is not None:
            obj.link = data.link
        if data.tags is not None:
            obj.tags = json.dumps(data.tags)
        if data.text is not None:
            obj.text = data.text
        s.add(obj)
        s.commit()
        s.refresh(obj)
        result = obj.model_dump()
        result["tags"] = json.loads(obj.tags) if obj.tags else []
        return result


@app.delete("/objects/{id}")
def delete_object(id: int, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        obj = _require_object(s, id, uid)
        for r in s.exec(
            select(ObjRelationship).where(
                or_(ObjRelationship.obj1_id == id, ObjRelationship.obj2_id == id)
            )
        ).all():
            s.delete(r)
        for n in s.exec(select(Note).where(Note.object_id == id)).all():
            s.delete(n)
        pos = s.exec(select(CanvasPosition).where(CanvasPosition.object_id == id)).first()
        if pos:
            s.delete(pos)
        s.delete(obj)
        s.commit()
        return {"ok": True}


# ─── Positions ────────────────────────────────────────────────────────────────

@app.put("/positions/{id}")
def update_position(id: int, data: PositionUpdate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        pos = s.get(CanvasPosition, id)
        if not pos:
            raise HTTPException(404)
        _require_mindmap(s, pos.mindmap_id, uid)
        pos.x = data.x
        pos.y = data.y
        s.add(pos)
        s.commit()
        return {"ok": True}


# ─── Relationships ────────────────────────────────────────────────────────────

@app.post("/relationships", response_model=ObjRelationship)
def create_relationship(data: RelationshipCreate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        _require_mindmap(s, data.mindmap_id, uid)
        r = ObjRelationship(**data.model_dump())
        s.add(r)
        s.commit()
        s.refresh(r)
        return r


@app.patch("/relationships/{id}", response_model=ObjRelationship)
def update_relationship(id: int, data: RelationshipUpdate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        r = s.get(ObjRelationship, id)
        if not r:
            raise HTTPException(404)
        _require_mindmap(s, r.mindmap_id, uid)
        if data.description is not None:
            r.description = data.description
        s.add(r)
        s.commit()
        s.refresh(r)
        return r


@app.delete("/relationships/{id}")
def delete_relationship(id: int, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        r = s.get(ObjRelationship, id)
        if not r:
            raise HTTPException(404)
        _require_mindmap(s, r.mindmap_id, uid)
        s.delete(r)
        s.commit()
        return {"ok": True}


# ─── Notes ────────────────────────────────────────────────────────────────────

@app.get("/objects/{id}/notes", response_model=List[Note])
def list_notes(id: int, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        _require_object(s, id, uid)
        return s.exec(select(Note).where(Note.object_id == id)).all()


@app.post("/objects/{id}/notes", response_model=Note)
def create_note(id: int, data: NoteCreate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        _require_object(s, id, uid)
        note = Note(object_id=id, content=data.content)
        s.add(note)
        s.commit()
        s.refresh(note)
        return note


@app.patch("/notes/{id}", response_model=Note)
def update_note(id: int, data: NoteCreate, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        note = s.get(Note, id)
        if not note:
            raise HTTPException(404)
        _require_object(s, note.object_id, uid)
        note.content = data.content
        s.add(note)
        s.commit()
        s.refresh(note)
        return note


@app.delete("/notes/{id}")
def delete_note(id: int, request: Request):
    uid = _current_user_id(request)
    with Session(engine) as s:
        note = s.get(Note, id)
        if not note:
            raise HTTPException(404)
        _require_object(s, note.object_id, uid)
        s.delete(note)
        s.commit()
        return {"ok": True}


# ─── SPA static file serving (must be last) ───────────────────────────────────

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    file_path = STATIC_DIR / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    index_path = file_path / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    return FileResponse(STATIC_DIR / "index.html")
