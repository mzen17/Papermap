<script lang="ts">
	import { onMount } from 'svelte';
	import {
		SvelteFlow,
		Background,
		BackgroundVariant,
		Controls,
		useSvelteFlow,
		type Node,
		type Edge,
		type Connection,
	} from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';

	import { api } from '$lib/api';
	import type { CanvasObject, Relationship } from '$lib/types';
	import PaperNodeComponent from './PaperNode.svelte';
	import TextNodeComponent from './TextNode.svelte';
	import NotesPanel from './NotesPanel.svelte';

	let {
		mindmapId,
		initialObjects,
		initialRelationships,
	}: {
		mindmapId: number;
		initialObjects: CanvasObject[];
		initialRelationships: Relationship[];
	} = $props();

	// ─── Notes panel ──────────────────────────────────────────────────────────────

	let notesObjectId = $state<number | null>(null);
	let noteCounts = $state<Record<number, number>>({});

	function openNotesFor(objectId: number) {
		notesObjectId = objectId;
	}

	function handleNoteCountChange(objectId: number, count: number) {
		noteCounts[objectId] = count;
		nodes = nodes.map((n) =>
			n.id === String(objectId)
				? { ...n, data: { ...n.data, noteCount: count } }
				: n
		);
	}

	function objToNode(obj: CanvasObject): Node {
		return {
			id: String(obj.id),
			type: obj.type,
			position: { x: obj.x, y: obj.y },
			data: { ...obj, noteCount: noteCounts[obj.id] ?? obj.note_count ?? 0, onOpenNotes: openNotesFor },
		};
	}

	function relToEdge(rel: Relationship): Edge {
		return {
			id: String(rel.id),
			source: String(rel.obj1_id),
			target: String(rel.obj2_id),
			label: rel.description || undefined,
			type: 'default',
			data: { relId: rel.id, description: rel.description },
		};
	}

	// Seed note counts from initial data before building nodes
	for (const obj of initialObjects) {
		if (obj.note_count !== undefined) noteCounts[obj.id] = obj.note_count;
	}

	let nodes = $state<Node[]>(initialObjects.map(objToNode));
	let edges = $state<Edge[]>(initialRelationships.map(relToEdge));

	const nodeTypes = { paper: PaperNodeComponent, text: TextNodeComponent };

	const { screenToFlowPosition } = useSvelteFlow();

	// ─── Selection & edit ─────────────────────────────────────────────────────

	let selectedNodeId = $state<string | null>(null);
	let selectedEdgeId = $state<string | null>(null);
	let editTitle = $state('');
	let editLink = $state('');
	let editTags = $state('');
	let editText = $state('');
	let editRelDesc = $state('');
	let saving = $state(false);

	let selectedNode = $derived(selectedNodeId ? nodes.find((n) => n.id === selectedNodeId) : null);
	let selectedEdge = $derived(selectedEdgeId ? edges.find((e) => e.id === selectedEdgeId) : null);

	// ─── Mode ─────────────────────────────────────────────────────────────────

	type Mode = 'select' | 'add-paper' | 'add-text';
	let mode = $state<Mode>('select');

	// ─── Modals ───────────────────────────────────────────────────────────────

	let showPaperModal = $state(false);
	let pendingPos = $state({ x: 200, y: 200 });
	let paperTitle = $state('');
	let paperLink = $state('');
	let paperTags = $state('');
	let creatingPaper = $state(false);

	let showTextModal = $state(false);
	let textContent = $state('');
	let creatingText = $state(false);

	// ─── SvelteFlow event handlers ────────────────────────────────────────────

	function handleNodeClick({ node }: { node: Node }) {
		selectedNodeId = node.id;
		selectedEdgeId = null;
		const d = node.data as CanvasObject;
		editTitle = d.title ?? '';
		editLink = d.link ?? '';
		editTags = (d.tags ?? []).join(', ');
		editText = d.text ?? '';
	}

	function handleEdgeClick({ edge }: { edge: Edge }) {
		selectedEdgeId = edge.id;
		selectedNodeId = null;
		editRelDesc = (edge.data as any)?.description ?? '';
	}

	function handlePaneClick({ event }: { event: MouseEvent }) {
		if (mode === 'add-paper') {
			pendingPos = screenToFlowPosition({ x: event.clientX, y: event.clientY });
			showPaperModal = true;
			mode = 'select';
			return;
		}
		if (mode === 'add-text') {
			pendingPos = screenToFlowPosition({ x: event.clientX, y: event.clientY });
			showTextModal = true;
			mode = 'select';
			return;
		}
		selectedNodeId = null;
		selectedEdgeId = null;
	}

	async function handleConnect(connection: Connection) {
		const { source, target } = connection;
		if (!source || !target) return;
		const tempId = `temp-${Date.now()}`;
		edges = [...edges, { id: tempId, source, target, type: 'default', animated: true }];
		try {
			const rel = await api.createRelationship({
				mindmap_id: mindmapId,
				obj1_id: Number(source),
				obj2_id: Number(target),
			});
			edges = edges.map((e) => (e.id === tempId ? relToEdge(rel) : e));
		} catch {
			edges = edges.filter((e) => e.id !== tempId);
		}
	}

	function handleNodeDragStop({ targetNode }: { targetNode: Node; nodes: Node[] }) {
		const posId = (targetNode.data as CanvasObject).pos_id;
		if (posId) {
			api.updatePosition(posId, targetNode.position.x, targetNode.position.y);
		}
	}

	// ─── CRUD ─────────────────────────────────────────────────────────────────

	async function submitPaperForm() {
		if (creatingPaper) return;
		creatingPaper = true;
		try {
			const obj = await api.createObject({
				mindmap_id: mindmapId,
				type: 'paper',
				title: paperTitle,
				link: paperLink,
				tags: paperTags.split(',').map((t) => t.trim()).filter(Boolean),
				x: pendingPos.x,
				y: pendingPos.y,
			});
			nodes = [...nodes, objToNode(obj)];
			selectedNodeId = String(obj.id);
			editTitle = obj.title ?? '';
			editLink = obj.link ?? '';
			editTags = (obj.tags ?? []).join(', ');
			editText = '';
		} finally {
			showPaperModal = false;
			paperTitle = '';
			paperLink = '';
			paperTags = '';
			creatingPaper = false;
		}
	}

	async function submitTextForm() {
		if (creatingText) return;
		creatingText = true;
		try {
			const obj = await api.createObject({
				mindmap_id: mindmapId,
				type: 'text',
				text: textContent,
				x: pendingPos.x,
				y: pendingPos.y,
			});
			nodes = [...nodes, objToNode(obj)];
			selectedNodeId = String(obj.id);
			editText = obj.text ?? '';
			editTitle = '';
			editLink = '';
			editTags = '';
		} finally {
			showTextModal = false;
			textContent = '';
			creatingText = false;
		}
	}

	async function saveEdit() {
		if (!selectedNodeId || saving) return;
		saving = true;
		try {
			const updated = await api.updateObject(Number(selectedNodeId), {
				title: editTitle,
				link: editLink,
				tags: editTags.split(',').map((t) => t.trim()).filter(Boolean),
				text: editText,
			});
			nodes = nodes.map((n) =>
				n.id === selectedNodeId ? { ...n, data: { ...n.data, ...updated } } : n
			);
		} finally {
			saving = false;
		}
	}

	async function saveRelDesc() {
		if (!selectedEdgeId || saving) return;
		saving = true;
		try {
			await api.updateRelationship(Number(selectedEdgeId), editRelDesc);
			edges = edges.map((e) =>
				e.id === selectedEdgeId
					? { ...e, label: editRelDesc || undefined, data: { ...e.data, description: editRelDesc } }
					: e
			);
		} finally {
			saving = false;
		}
	}

	async function deleteSelectedNode() {
		if (!selectedNodeId) return;
		await api.deleteObject(Number(selectedNodeId));
		edges = edges.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId);
		nodes = nodes.filter((n) => n.id !== selectedNodeId);
		selectedNodeId = null;
	}

	async function deleteSelectedEdge() {
		if (!selectedEdgeId) return;
		await api.deleteRelationship(Number(selectedEdgeId));
		edges = edges.filter((e) => e.id !== selectedEdgeId);
		selectedEdgeId = null;
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
		if (e.key === 'Delete' || e.key === 'Backspace') {
			if (selectedNodeId) deleteSelectedNode();
			else if (selectedEdgeId) deleteSelectedEdge();
		}
		if (e.key === 'Escape') mode = 'select';
	}

	onMount(() => {
		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	});
</script>

<div class="flex flex-col flex-1 min-h-0">
	<!-- Toolbar -->
	<div class="flex items-center gap-1 px-3 py-2 bg-white border-b border-slate-200 shrink-0">
		<span class="text-xs font-semibold text-slate-400 uppercase tracking-widest mr-2">Tools</span>

		<button class="tool-btn" class:active={mode === 'select'} onclick={() => (mode = 'select')}>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5" />
			</svg>
			Select
		</button>

		<button class="tool-btn" class:active={mode === 'add-paper'} onclick={() => (mode = 'add-paper')}>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
					d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414A1 1 0 0119 9.414V19a2 2 0 01-2 2z" />
			</svg>
			Paper
		</button>

		<button class="tool-btn" class:active={mode === 'add-text'} onclick={() => (mode = 'add-text')}>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h10M4 18h7" />
			</svg>
			Text
		</button>

		<div class="w-px h-5 bg-slate-200 mx-1"></div>

		{#if selectedNodeId}
			<button class="tool-btn text-red-500 hover:bg-red-50" onclick={deleteSelectedNode}>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
				</svg>
				Delete Node
			</button>
		{/if}
		{#if selectedEdgeId}
			<button class="tool-btn text-red-500 hover:bg-red-50" onclick={deleteSelectedEdge}>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
				</svg>
				Delete Link
			</button>
		{/if}

		{#if mode !== 'select'}
			<span class="text-xs text-blue-600 ml-2 italic">
				{mode === 'add-paper' ? 'Click canvas to place paper…' : 'Click canvas to place text…'}
			</span>
		{/if}

		<span class="text-xs text-slate-400 ml-auto">Drag node handles to connect</span>
	</div>

	<!-- Canvas + Side panel -->
	<div class="flex flex-1 min-h-0">
		<div class="flex-1 min-h-0" style:cursor={mode !== 'select' ? 'crosshair' : undefined}>
			<SvelteFlow
				bind:nodes
				bind:edges
				{nodeTypes}
				fitView
				deleteKey={null}
				onnodeclick={handleNodeClick}
				onedgeclick={handleEdgeClick}
				onpaneclick={handlePaneClick}
				onconnect={handleConnect}
				onnodedragstop={handleNodeDragStop}
			>
				<Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#cbd5e1" />
				<Controls />
			</SvelteFlow>
		</div>

		{#if selectedNode || selectedEdge}
			<div class="w-72 border-l border-slate-200 bg-white flex flex-col overflow-y-auto shrink-0">
				<div class="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
					<span class="text-xs font-semibold text-slate-500 uppercase tracking-widest">
						{selectedNode ? (selectedNode.type === 'paper' ? 'Paper' : 'Text Group') : 'Relationship'}
					</span>
					<button class="text-slate-300 hover:text-slate-500 text-xl leading-none"
						onclick={() => { selectedNodeId = null; selectedEdgeId = null; }}>×</button>
				</div>

				<div class="p-4 flex flex-col gap-3 flex-1">
					{#if selectedNode?.type === 'paper'}
						<label class="field">
							<span>Title</span>
							<input class="input" type="text" bind:value={editTitle} placeholder="Paper title" />
						</label>
						<label class="field">
							<span>Link / URL</span>
							<input class="input" type="url" bind:value={editLink} placeholder="https://…" />
						</label>
						<label class="field">
							<span>Tags <span class="font-normal text-slate-400">(comma-separated)</span></span>
							<input class="input" type="text" bind:value={editTags} placeholder="ml, nlp, survey" />
						</label>
					{:else if selectedNode?.type === 'text'}
						<label class="field">
							<span>Content</span>
							<textarea class="input resize-none h-28" bind:value={editText} placeholder="Group label or note…"></textarea>
						</label>
					{:else if selectedEdge}
						<label class="field">
							<span>Label</span>
							<input class="input" type="text" bind:value={editRelDesc} placeholder="e.g. extends, cites…" />
						</label>
					{/if}

					<button
						class="mt-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium py-2 rounded-lg transition-colors"
						disabled={saving}
						onclick={selectedEdge ? saveRelDesc : saveEdit}
					>
						{saving ? 'Saving…' : 'Save'}
					</button>

					<div class="border-t border-slate-100 pt-3">
						<button
							class="text-red-500 hover:text-red-700 text-sm"
							onclick={selectedEdge ? deleteSelectedEdge : deleteSelectedNode}
						>Delete {selectedEdge ? 'relationship' : 'node'}</button>
					</div>

					{#if selectedNode}
						{@const nodeRels = edges.filter((e) => e.source === selectedNodeId || e.target === selectedNodeId)}
						{#if nodeRels.length}
							<div class="border-t border-slate-100 pt-3">
								<p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">Connections</p>
								{#each nodeRels as e}
									{@const otherId = e.source === selectedNodeId ? e.target : e.source}
									{@const other = nodes.find((n) => n.id === otherId)}
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<div
										class="text-xs text-slate-600 hover:text-blue-600 cursor-pointer mb-1 flex items-center gap-1"
										onclick={() => { selectedEdgeId = e.id; editRelDesc = (e.data as any)?.description ?? ''; selectedNodeId = null; }}
										onkeydown={(ev) => ev.key === 'Enter' && (selectedEdgeId = e.id)}
									>
										<span class="text-slate-300">→</span>
										{(other?.data as any)?.title ?? (other?.data as any)?.text ?? `#${otherId}`}
										{#if e.label}<span class="text-slate-400 italic">({e.label})</span>{/if}
									</div>
								{/each}
							</div>
						{/if}
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>

{#if notesObjectId !== null}
	{@const notesNode = nodes.find((n) => n.id === String(notesObjectId))}
	<NotesPanel
		objectId={notesObjectId}
		objectTitle={(notesNode?.data as any)?.title ?? ''}
		onclose={() => (notesObjectId = null)}
		onnotecountchange={handleNoteCountChange}
	/>
{/if}

{#if showPaperModal}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="fixed inset-0 bg-black/30 z-50 flex items-center justify-center"
		onpointerdown={(e) => { if (e.target === e.currentTarget) showPaperModal = false; }}>
		<div class="bg-white rounded-2xl shadow-2xl w-96 p-6">
			<h2 class="text-base font-semibold text-slate-800 mb-4">Add Paper</h2>
			<form class="flex flex-col gap-3" onsubmit={(e) => { e.preventDefault(); submitPaperForm(); }}>
				<label class="field">
					<span>Title</span>
					<input class="input" type="text" bind:value={paperTitle} placeholder="Paper title" autofocus />
				</label>
				<label class="field">
					<span>Link / URL</span>
					<input class="input" type="url" bind:value={paperLink} placeholder="https://…" />
				</label>
				<label class="field">
					<span>Tags <span class="font-normal text-slate-400">(comma-separated)</span></span>
					<input class="input" type="text" bind:value={paperTags} placeholder="ml, nlp, survey" />
				</label>
				<div class="flex gap-2 mt-1">
					<button type="submit" disabled={creatingPaper}
						class="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium py-2 rounded-lg transition-colors">Add</button>
					<button type="button" onclick={() => (showPaperModal = false)}
						class="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2 rounded-lg transition-colors">Cancel</button>
				</div>
			</form>
		</div>
	</div>
{/if}

{#if showTextModal}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="fixed inset-0 bg-black/30 z-50 flex items-center justify-center"
		onpointerdown={(e) => { if (e.target === e.currentTarget) showTextModal = false; }}>
		<div class="bg-white rounded-2xl shadow-2xl w-80 p-6">
			<h2 class="text-base font-semibold text-slate-800 mb-4">Add Text Group</h2>
			<form class="flex flex-col gap-3" onsubmit={(e) => { e.preventDefault(); submitTextForm(); }}>
				<label class="field">
					<span>Content</span>
					<textarea class="input resize-none h-24" bind:value={textContent}
						placeholder="Group label or annotation…" autofocus></textarea>
				</label>
				<div class="flex gap-2">
					<button type="submit" disabled={creatingText}
						class="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium py-2 rounded-lg transition-colors">Add</button>
					<button type="button" onclick={() => (showTextModal = false)}
						class="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2 rounded-lg transition-colors">Cancel</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<style>
	.tool-btn {
		display: flex; align-items: center; gap: 4px;
		font-size: 0.75rem; font-weight: 500; color: #475569;
		padding: 4px 10px; border-radius: 6px; border: 1px solid transparent;
		cursor: pointer; background: none; transition: background-color 0.15s, color 0.15s;
	}
	.tool-btn:hover { background-color: #f1f5f9; color: #1e293b; }
	.tool-btn.active { background-color: #eff6ff; color: #2563eb; border-color: #bfdbfe; }

	.field { display: flex; flex-direction: column; gap: 4px; font-size: 0.75rem; font-weight: 600; color: #475569; }
	.input {
		border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px 10px;
		font-size: 0.8rem; color: #1e293b; background: #f8fafc; outline: none; width: 100%;
		transition: border-color 0.15s, box-shadow 0.15s;
	}
	.input:focus { border-color: #93c5fd; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); background: #fff; }

	:global(.svelte-flow) { background: #f1f5f9; }
	:global(.svelte-flow__edge-path) { stroke: #94a3b8; stroke-width: 1.5; }
	:global(.svelte-flow__edge.selected .svelte-flow__edge-path) { stroke: #3b82f6; stroke-width: 2; }
	:global(.svelte-flow__handle) { width: 8px; height: 8px; background: #94a3b8; border: 2px solid white; }
	:global(.svelte-flow__handle:hover) { background: #3b82f6; }
	:global(.svelte-flow__controls) { box-shadow: 0 1px 4px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }
</style>
