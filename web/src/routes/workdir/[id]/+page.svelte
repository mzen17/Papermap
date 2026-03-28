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
				<div class="flex items-center justify-between bg-white border border-slate-200 rounded-xl px-5 py-4 shadow-sm hover:shadow-md transition-shadow group">
					<a
						href="/project/{p.id}"
						class="font-medium text-slate-800 hover:text-blue-600 transition-colors flex-1"
					>
						{p.name}
					</a>
					<button
						onclick={() => remove(p.id)}
						class="text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 ml-4 text-lg leading-none"
						title="Delete project"
					>
						×
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>
