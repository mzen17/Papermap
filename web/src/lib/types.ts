export interface User {
	id: number;
	username: string;
}

export interface Workdir {
	id: number;
	name: string;
}

export interface Project {
	id: number;
	name: string;
	workdir_id: number;
}

export interface MindMap {
	id: number;
	name: string;
	project_id: number;
}

export type NodeType = 'paper' | 'text';

export interface CanvasObject {
	id: number;
	mindmap_id: number;
	type: NodeType;
	// paper fields
	title?: string;
	link?: string;
	tags: string[];
	// text field
	text?: string;
	// canvas position
	x: number;
	y: number;
	pos_id?: number;
	note_count?: number;
}

export interface Note {
	id: number;
	object_id: number;
	content: string;
}

export interface Relationship {
	id: number;
	mindmap_id: number;
	obj1_id: number;
	obj2_id: number;
	description?: string;
}

export interface MindMapFull {
	mindmap: MindMap;
	objects: CanvasObject[];
	relationships: Relationship[];
}
