import type { CanvasObject, MindMap, MindMapFull, Note, Project, Relationship, Workdir } from './types';

const BASE = 'http://localhost:8000';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(BASE + path, {
		headers: { 'Content-Type': 'application/json' },
		...init,
	});
	if (!res.ok) throw new Error(`API ${init?.method ?? 'GET'} ${path} → ${res.status}`);
	return res.json() as Promise<T>;
}

export const api = {
	// Workdirs
	listWorkdirs: () => req<Workdir[]>('/workdirs'),
	createWorkdir: (name: string) =>
		req<Workdir>('/workdirs', { method: 'POST', body: JSON.stringify({ name }) }),
	deleteWorkdir: (id: number) => req<{ ok: boolean }>(`/workdirs/${id}`, { method: 'DELETE' }),

	// Projects
	listProjects: (workdirId: number) => req<Project[]>(`/workdirs/${workdirId}/projects`),
	createProject: (name: string, workdir_id: number) =>
		req<Project>('/projects', { method: 'POST', body: JSON.stringify({ name, workdir_id }) }),
	deleteProject: (id: number) => req<{ ok: boolean }>(`/projects/${id}`, { method: 'DELETE' }),

	// MindMaps
	listMindMaps: (projectId: number) => req<MindMap[]>(`/projects/${projectId}/mindmaps`),
	createMindMap: (name: string, project_id: number) =>
		req<MindMap>('/mindmaps', { method: 'POST', body: JSON.stringify({ name, project_id }) }),
	deleteMindMap: (id: number) => req<{ ok: boolean }>(`/mindmaps/${id}`, { method: 'DELETE' }),
	getMindMapFull: (id: number) => req<MindMapFull>(`/mindmaps/${id}/full`),

	// Objects
	createObject: (data: {
		mindmap_id: number;
		type: string;
		title?: string;
		link?: string;
		tags?: string[];
		text?: string;
		x: number;
		y: number;
	}) => req<CanvasObject>('/objects', { method: 'POST', body: JSON.stringify(data) }),
	updateObject: (id: number, data: { title?: string; link?: string; tags?: string[]; text?: string }) =>
		req<CanvasObject>(`/objects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
	deleteObject: (id: number) => req<{ ok: boolean }>(`/objects/${id}`, { method: 'DELETE' }),

	// Positions
	updatePosition: (posId: number, x: number, y: number) =>
		req<{ ok: boolean }>(`/positions/${posId}`, {
			method: 'PUT',
			body: JSON.stringify({ x, y }),
		}),

	// Notes
	listNotes: (objectId: number) => req<Note[]>(`/objects/${objectId}/notes`),
	createNote: (objectId: number, content: string) =>
		req<Note>(`/objects/${objectId}/notes`, { method: 'POST', body: JSON.stringify({ content }) }),
	updateNote: (id: number, content: string) =>
		req<Note>(`/notes/${id}`, { method: 'PATCH', body: JSON.stringify({ content }) }),
	deleteNote: (id: number) => req<{ ok: boolean }>(`/notes/${id}`, { method: 'DELETE' }),

	// Relationships
	createRelationship: (data: {
		mindmap_id: number;
		obj1_id: number;
		obj2_id: number;
		description?: string;
	}) => req<Relationship>('/relationships', { method: 'POST', body: JSON.stringify(data) }),
	updateRelationship: (id: number, description: string) =>
		req<Relationship>(`/relationships/${id}`, {
			method: 'PATCH',
			body: JSON.stringify({ description }),
		}),
	deleteRelationship: (id: number) =>
		req<{ ok: boolean }>(`/relationships/${id}`, { method: 'DELETE' }),
};
