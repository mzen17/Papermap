from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, Session, create_engine, select, or_
from typing import Optional, List
import json

DATABASE_URL = "sqlite:///./papermap.db"
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

app = FastAPI(title="Papermap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Table Models ─────────────────────────────────────────────────────────────

class Workdir(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


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

class WorkdirCreate(SQLModel):
    name: str


class ProjectCreate(SQLModel):
    name: str
    workdir_id: int


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


# ─── Cascade Helpers ──────────────────────────────────────────────────────────

def _cascade_delete_mindmap(s: Session, mid: int):
    mm = s.get(MindMap, mid)
    if not mm:
        return
    for r in s.exec(select(ObjRelationship).where(ObjRelationship.mindmap_id == mid)).all():
        s.delete(r)
    for pos in s.exec(select(CanvasPosition).where(CanvasPosition.mindmap_id == mid)).all():
        s.delete(pos)
    for o in s.exec(select(MapObject).where(MapObject.mindmap_id == mid)).all():
        s.delete(o)
    s.delete(mm)


def _cascade_delete_project(s: Session, pid: int):
    p = s.get(Project, pid)
    if not p:
        return
    for mm in s.exec(select(MindMap).where(MindMap.project_id == pid)).all():
        _cascade_delete_mindmap(s, mm.id)
    s.delete(p)


# ─── Workdirs ─────────────────────────────────────────────────────────────────

@app.get("/workdirs", response_model=List[Workdir])
def list_workdirs():
    with Session(engine) as s:
        return s.exec(select(Workdir)).all()


@app.post("/workdirs", response_model=Workdir)
def create_workdir(data: WorkdirCreate):
    with Session(engine) as s:
        w = Workdir(name=data.name)
        s.add(w)
        s.commit()
        s.refresh(w)
        return w


@app.delete("/workdirs/{id}")
def delete_workdir(id: int):
    with Session(engine) as s:
        w = s.get(Workdir, id)
        if not w:
            raise HTTPException(404)
        for p in s.exec(select(Project).where(Project.workdir_id == id)).all():
            _cascade_delete_project(s, p.id)
        s.delete(w)
        s.commit()
        return {"ok": True}


# ─── Projects ─────────────────────────────────────────────────────────────────

@app.get("/workdirs/{workdir_id}/projects", response_model=List[Project])
def list_projects(workdir_id: int):
    with Session(engine) as s:
        return s.exec(select(Project).where(Project.workdir_id == workdir_id)).all()


@app.post("/projects", response_model=Project)
def create_project(data: ProjectCreate):
    with Session(engine) as s:
        p = Project(name=data.name, workdir_id=data.workdir_id)
        s.add(p)
        s.commit()
        s.refresh(p)
        return p


@app.delete("/projects/{id}")
def delete_project(id: int):
    with Session(engine) as s:
        _cascade_delete_project(s, id)
        s.commit()
        return {"ok": True}


# ─── MindMaps ─────────────────────────────────────────────────────────────────

@app.get("/projects/{project_id}/mindmaps", response_model=List[MindMap])
def list_mindmaps(project_id: int):
    with Session(engine) as s:
        return s.exec(select(MindMap).where(MindMap.project_id == project_id)).all()


@app.post("/mindmaps", response_model=MindMap)
def create_mindmap(data: MindMapCreate):
    with Session(engine) as s:
        mm = MindMap(name=data.name, project_id=data.project_id)
        s.add(mm)
        s.commit()
        s.refresh(mm)
        return mm


@app.delete("/mindmaps/{id}")
def delete_mindmap(id: int):
    with Session(engine) as s:
        _cascade_delete_mindmap(s, id)
        s.commit()
        return {"ok": True}


@app.get("/mindmaps/{id}/full")
def get_mindmap_full(id: int):
    with Session(engine) as s:
        mm = s.get(MindMap, id)
        if not mm:
            raise HTTPException(404)
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
def create_object(data: MapObjectCreate):
    with Session(engine) as s:
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
def update_object(id: int, data: MapObjectUpdate):
    with Session(engine) as s:
        obj = s.get(MapObject, id)
        if not obj:
            raise HTTPException(404)
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
def delete_object(id: int):
    with Session(engine) as s:
        obj = s.get(MapObject, id)
        if not obj:
            raise HTTPException(404)
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
def update_position(id: int, data: PositionUpdate):
    with Session(engine) as s:
        pos = s.get(CanvasPosition, id)
        if not pos:
            raise HTTPException(404)
        pos.x = data.x
        pos.y = data.y
        s.add(pos)
        s.commit()
        return {"ok": True}


# ─── Relationships ────────────────────────────────────────────────────────────

@app.post("/relationships", response_model=ObjRelationship)
def create_relationship(data: RelationshipCreate):
    with Session(engine) as s:
        r = ObjRelationship(**data.model_dump())
        s.add(r)
        s.commit()
        s.refresh(r)
        return r


@app.patch("/relationships/{id}", response_model=ObjRelationship)
def update_relationship(id: int, data: RelationshipUpdate):
    with Session(engine) as s:
        r = s.get(ObjRelationship, id)
        if not r:
            raise HTTPException(404)
        if data.description is not None:
            r.description = data.description
        s.add(r)
        s.commit()
        s.refresh(r)
        return r


@app.delete("/relationships/{id}")
def delete_relationship(id: int):
    with Session(engine) as s:
        r = s.get(ObjRelationship, id)
        if not r:
            raise HTTPException(404)
        s.delete(r)
        s.commit()
        return {"ok": True}



# ─── Notes ────────────────────────────────────────────────────────────────────

@app.get("/objects/{id}/notes", response_model=List[Note])
def list_notes(id: int):
    with Session(engine) as s:
        return s.exec(select(Note).where(Note.object_id == id)).all()


@app.post("/objects/{id}/notes", response_model=Note)
def create_note(id: int, data: NoteCreate):
    with Session(engine) as s:
        note = Note(object_id=id, content=data.content)
        s.add(note)
        s.commit()
        s.refresh(note)
        return note


@app.patch("/notes/{id}", response_model=Note)
def update_note(id: int, data: NoteCreate):
    with Session(engine) as s:
        note = s.get(Note, id)
        if not note:
            raise HTTPException(404)
        note.content = data.content
        s.add(note)
        s.commit()
        s.refresh(note)
        return note


@app.delete("/notes/{id}")
def delete_note(id: int):
    with Session(engine) as s:
        note = s.get(Note, id)
        if not note:
            raise HTTPException(404)
        s.delete(note)
        s.commit()
        return {"ok": True}
