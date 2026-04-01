<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { api } from '$lib/api';
	import type { Project, Workdir } from '$lib/types';

	const workdirId = Number($page.params.id);

	let workdir = $state<Workdir | null>(null);
	let projects = $state<Project[]>([]);
	let newName = $state('');
	let loading = $state(true);
	let creating = $state(false);
	let editingId = $state<number | null>(null);
	let editingName = $state('');

	onMount(async () => {
		const [wds, projs] = await Promise.all([
			api.listWorkdirs(),
			api.listProjects(workdirId),
		]);
		workdir = wds.find((w) => w.id === workdirId) ?? null;
		projects = projs;
		loading = false;
	});

	async function create() {
		if (!newName.trim()) return;
		creating = true;
		const p = await api.createProject(newName.trim(), workdirId);
		projects.push(p);
		newName = '';
		creating = false;
	}

	async function remove(id: number) {
		await api.deleteProject(id);
		projects = projects.filter((p) => p.id !== id);
	}

	function startEdit(p: Project) {
		editingId = p.id;
		editingName = p.name;
	}

	async function saveEdit(id: number) {
		if (editingId !== id) return;
		const name = editingName.trim();
		editingId = null;
		if (!name) return;
		const updated = await api.renameProject(id, name);
		const idx = projects.findIndex((p) => p.id === id);
		if (idx !== -1) projects[idx] = updated;
	}
</script>

<div class="p-8 max-w-3xl mx-auto w-full">
	<div class="mb-2">
		<a href="/" class="text-sm text-slate-400 hover:text-slate-600 transition-colors">← Workspaces</a>
	</div>
	<div class="mb-8">
		<h1 class="text-2xl font-bold text-slate-800 mb-1">{workdir?.name ?? '…'}</h1>
		<p class="text-slate-500 text-sm">Projects in this workspace.</p>
	</div>

	<form
		class="flex gap-2 mb-8"
		onsubmit={(e) => { e.preventDefault(); create(); }}
	>
		<input
			class="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
			placeholder="New project name…"
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
	{:else if projects.length === 0}
		<p class="text-slate-400 text-sm">No projects yet. Create one above.</p>
	{:else}
		<div class="grid gap-3">
			{#each projects as p (p.id)}
				<div class="flex items-center bg-white border border-slate-200 rounded-xl px-5 py-4 shadow-sm hover:shadow-md transition-shadow group">
					{#if editingId === p.id}
						<form
							class="flex-1 flex gap-2"
							onsubmit={(e) => { e.preventDefault(); saveEdit(p.id); }}
						>
							<input
								class="flex-1 border border-slate-300 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
								bind:value={editingName}
								onblur={() => saveEdit(p.id)}
								onkeydown={(e) => { if (e.key === 'Escape') { e.preventDefault(); editingId = null; } }}
								autofocus
							/>
						</form>
					{:else}
						<a
							href="/project/{p.id}"
							class="font-medium text-slate-800 hover:text-blue-600 transition-colors flex-1"
						>
							{p.name}
						</a>
						<button
							onclick={() => startEdit(p)}
							class="text-slate-300 hover:text-blue-500 transition-colors opacity-0 group-hover:opacity-100 ml-4"
							title="Rename project"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
									d="M15.232 5.232l3.536 3.536M9 13l6.586-6.586a2 2 0 012.828 2.828L11.828 15.828a2 2 0 01-1.414.586H7v-3.414a2 2 0 01.586-1.414z"/>
							</svg>
						</button>
					{/if}
					<button
						onclick={() => remove(p.id)}
						class="text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 ml-3 text-lg leading-none"
						title="Delete project"
					>
						×
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>
