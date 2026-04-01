<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import type { Workdir } from '$lib/types';

	let workdirs = $state<Workdir[]>([]);
	let newName = $state('');
	let loading = $state(true);
	let creating = $state(false);
	let editingId = $state<number | null>(null);
	let editingName = $state('');

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

	function startEdit(w: Workdir) {
		editingId = w.id;
		editingName = w.name;
	}

	async function saveEdit(id: number) {
		if (editingId !== id) return;
		const name = editingName.trim();
		editingId = null;
		if (!name) return;
		const updated = await api.renameWorkdir(id, name);
		const idx = workdirs.findIndex((w) => w.id === id);
		if (idx !== -1) workdirs[idx] = updated;
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
				<div class="flex items-center bg-white border border-slate-200 rounded-xl px-5 py-4 shadow-sm hover:shadow-md transition-shadow group">
					{#if editingId === w.id}
						<form
							class="flex-1 flex gap-2"
							onsubmit={(e) => { e.preventDefault(); saveEdit(w.id); }}
						>
							<input
								class="flex-1 border border-slate-300 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
								bind:value={editingName}
								onblur={() => saveEdit(w.id)}
								onkeydown={(e) => { if (e.key === 'Escape') { e.preventDefault(); editingId = null; } }}
								autofocus
							/>
						</form>
					{:else}
						<a
							href="/workdir/{w.id}"
							class="font-medium text-slate-800 hover:text-blue-600 transition-colors flex-1"
						>
							{w.name}
						</a>
						<button
							onclick={() => startEdit(w)}
							class="text-slate-300 hover:text-blue-500 transition-colors opacity-0 group-hover:opacity-100 ml-4"
							title="Rename workspace"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
									d="M15.232 5.232l3.536 3.536M9 13l6.586-6.586a2 2 0 012.828 2.828L11.828 15.828a2 2 0 01-1.414.586H7v-3.414a2 2 0 01.586-1.414z"/>
							</svg>
						</button>
					{/if}
					<button
						onclick={() => remove(w.id)}
						class="text-slate-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 ml-3 text-lg leading-none"
						title="Delete workspace"
					>
						×
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>
