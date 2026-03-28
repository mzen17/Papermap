<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { api } from '$lib/api';
	import type { MindMap, Project, Workdir } from '$lib/types';

	const projectId = Number($page.params.id);

	let project = $state<Project | null>(null);
	let workdir = $state<Workdir | null>(null);
	let mindmaps = $state<MindMap[]>([]);
	let newName = $state('');
	let loading = $state(true);
	let creating = $state(false);

	onMount(async () => {
		mindmaps = await api.listMindMaps(projectId);
		// Load project info for breadcrumb
		const allWorkdirs = await api.listWorkdirs();
		for (const wd of allWorkdirs) {
			const projs = await api.listProjects(wd.id);
			const found = projs.find((p) => p.id === projectId);
			if (found) {
				project = found;
				workdir = wd;
				break;
			}
		}
		loading = false;
	});

	async function create() {
		if (!newName.trim()) return;
		creating = true;
		const mm = await api.createMindMap(newName.trim(), projectId);
		mindmaps.push(mm);
		newName = '';
		creating = false;
	}

	async function remove(id: number) {
		await api.deleteMindMap(id);
		mindmaps = mindmaps.filter((m) => m.id !== id);
	}
</script>

<div class="p-8 max-w-3xl mx-auto w-full">
	<div class="mb-2 flex items-center gap-2 text-sm text-slate-400">
		<a href="/" class="hover:text-slate-600 transition-colors">Workspaces</a>
		{#if workdir}
			<span>/</span>
			<a href="/workdir/{workdir.id}" class="hover:text-slate-600 transition-colors">{workdir.name}</a>
		{/if}
		<span>/</span>
		<span class="text-slate-600">{project?.name ?? '…'}</span>
	</div>

	<div class="mb-8 mt-2">
		<h1 class="text-2xl font-bold text-slate-800 mb-1">{project?.name ?? '…'}</h1>
		<p class="text-slate-500 text-sm">Mind maps in this project.</p>
	</div>

	<form
		class="flex gap-2 mb-8"
		onsubmit={(e) => { e.preventDefault(); create(); }}
	>
		<input
			class="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
			placeholder="New mind map name…"
			bind:value={newName}
		/>
		<button
			type="submit"
			disabled={creating || !newName.trim()}
			class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
		>
			Create
		</button>
	</form>

	{#if loading}
		<p class="text-slate-400 text-sm">Loading…</p>
	{:else if mindmaps.length === 0}
		<p class="text-slate-400 text-sm">No mind maps yet. Create one above.</p>
	{:else}
		<div class="grid grid-cols-2 gap-4">
			{#each mindmaps as mm (mm.id)}
				<div class="group relative bg-white border border-slate-200 rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden">
					<a href="/mindmap/{mm.id}" class="block p-5">
						<div class="h-20 mb-3 bg-gradient-to-br from-blue-50 to-slate-100 rounded-lg flex items-center justify-center">
							<svg class="w-8 h-8 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<circle cx="12" cy="12" r="3" stroke-width="2"/>
								<circle cx="5" cy="5" r="2" stroke-width="2"/>
								<circle cx="19" cy="5" r="2" stroke-width="2"/>
								<circle cx="5" cy="19" r="2" stroke-width="2"/>
								<line x1="12" y1="9" x2="6.5" y2="6.5" stroke-width="2"/>
								<line x1="12" y1="9" x2="17.5" y2="6.5" stroke-width="2"/>
								<line x1="12" y1="15" x2="6.5" y2="17.5" stroke-width="2"/>
							</svg>
						</div>
						<p class="font-medium text-slate-800 text-sm">{mm.name}</p>
					</a>
					<button
						onclick={() => remove(mm.id)}
						class="absolute top-3 right-3 text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 text-lg leading-none"
						title="Delete mind map"
					>
						×
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>
