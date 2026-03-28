<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { Workdir } from '$lib/types';

	let workdirs = $state<Workdir[]>([]);
	let newName = $state('');
	let loading = $state(true);
	let creating = $state(false);

	onMount(async () => {
		workdirs = await api.listWorkdirs();
		loading = false;
	});

	async function create() {
		if (!newName.trim()) return;
		creating = true;
		const w = await api.createWorkdir(newName.trim());
		workdirs.push(w);
		newName = '';
		creating = false;
	}

	async function remove(id: number) {
		await api.deleteWorkdir(id);
		workdirs = workdirs.filter((w) => w.id !== id);
	}
</script>

<div class="p-8 max-w-3xl mx-auto w-full">
	<div class="mb-8">
		<h1 class="text-2xl font-bold text-slate-800 mb-1">Workspaces</h1>
		<p class="text-slate-500 text-sm">Organize your research into workspaces.</p>
	</div>

	<form
		class="flex gap-2 mb-8"
		onsubmit={(e) => { e.preventDefault(); create(); }}
	>
		<input
			class="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
			placeholder="New workspace name…"
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
	{:else if workdirs.length === 0}
		<p class="text-slate-400 text-sm">No workspaces yet. Create one above.</p>
	{:else}
		<div class="grid gap-3">
			{#each workdirs as w (w.id)}
				<div class="flex items-center justify-between bg-white border border-slate-200 rounded-xl px-5 py-4 shadow-sm hover:shadow-md transition-shadow group">
					<a
						href="/workdir/{w.id}"
						class="font-medium text-slate-800 hover:text-blue-600 transition-colors flex-1"
					>
						{w.name}
					</a>
					<button
						onclick={() => remove(w.id)}
						class="text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 ml-4 text-lg leading-none"
						title="Delete workspace"
					>
						×
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>
