<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { api } from '$lib/api';
	import type { CanvasObject, MindMap, Project, Relationship, Workdir } from '$lib/types';
	import Canvas from '$lib/components/Canvas.svelte';
	import { SvelteFlowProvider } from '@xyflow/svelte';

	const mindmapId = Number($page.params.id);

	let mindmap = $state<MindMap | null>(null);
	let project = $state<Project | null>(null);
	let workdir = $state<Workdir | null>(null);
	let objects = $state<CanvasObject[]>([]);
	let relationships = $state<Relationship[]>([]);
	let loading = $state(true);
	let error = $state('');

	onMount(async () => {
		try {
			const full = await api.getMindMapFull(mindmapId);
			mindmap = full.mindmap;
			objects = full.objects;
			relationships = full.relationships;

			// Breadcrumb: load project + workdir
			const allWorkdirs = await api.listWorkdirs();
			for (const wd of allWorkdirs) {
				const projs = await api.listProjects(wd.id);
				const found = projs.find((p) => p.id === full.mindmap.project_id);
				if (found) {
					project = found;
					workdir = wd;
					break;
				}
			}
		} catch (e: any) {
			error = e.message ?? 'Failed to load';
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>{mindmap?.name ?? 'Mind Map'} — Papermap</title>
</svelte:head>

<!-- Breadcrumb bar -->
<div class="px-4 py-2 bg-white border-b border-slate-200 flex items-center gap-2 text-xs text-slate-400 shrink-0">
	<a href="/" class="hover:text-slate-600 transition-colors">Workspaces</a>
	{#if workdir}
		<span>/</span>
		<a href="/workdir/{workdir.id}" class="hover:text-slate-600 transition-colors">{workdir.name}</a>
	{/if}
	{#if project}
		<span>/</span>
		<a href="/project/{project.id}" class="hover:text-slate-600 transition-colors">{project.name}</a>
	{/if}
	<span>/</span>
	<span class="text-slate-700 font-medium">{mindmap?.name ?? '…'}</span>
</div>

{#if loading}
	<div class="flex-1 flex items-center justify-center text-slate-400 text-sm">Loading…</div>
{:else if error}
	<div class="flex-1 flex items-center justify-center text-red-500 text-sm">{error}</div>
{:else}
	<div class="flex-1 flex flex-col overflow-hidden">
		<SvelteFlowProvider>
			<Canvas
				{mindmapId}
				initialObjects={objects}
				initialRelationships={relationships}
			/>
		</SvelteFlowProvider>
	</div>
{/if}
