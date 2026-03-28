<script lang="ts">
	import { api } from '$lib/api';
	import type { Note } from '$lib/types';

	let {
		objectId,
		objectTitle,
		onclose,
		onnotecountchange,
	}: {
		objectId: number;
		objectTitle: string;
		onclose: () => void;
		onnotecountchange: (objectId: number, count: number) => void;
	} = $props();

	let notes = $state<Note[]>([]);
	let loading = $state(true);
	let editingId = $state<number | null>(null);
	let editingContent = $state('');
	let adding = $state(false);
	let newContent = $state('');

	const PALETTE = [
		{ bg: '#fef9c3', border: '#fde68a' },
		{ bg: '#dcfce7', border: '#bbf7d0' },
		{ bg: '#dbeafe', border: '#bfdbfe' },
		{ bg: '#fce7f3', border: '#fbcfe8' },
		{ bg: '#ede9fe', border: '#ddd6fe' },
	];

	function palette(id: number) {
		return PALETTE[id % PALETTE.length];
	}

	$effect(() => {
		objectId;
		loadNotes();
	});

	async function loadNotes() {
		loading = true;
		notes = await api.listNotes(objectId);
		loading = false;
	}

	async function addNote() {
		if (adding) return;
		adding = true;
		const note = await api.createNote(objectId, newContent.trim());
		notes = [...notes, note];
		newContent = '';
		adding = false;
		onnotecountchange(objectId, notes.length);
	}

	async function deleteNote(id: number) {
		await api.deleteNote(id);
		notes = notes.filter((n) => n.id !== id);
		onnotecountchange(objectId, notes.length);
	}

	function startEdit(note: Note) {
		editingId = note.id;
		editingContent = note.content;
	}

	async function saveEdit(id: number) {
		if (editingId !== id) return;
		const updated = await api.updateNote(id, editingContent);
		notes = notes.map((n) => (n.id === id ? updated : n));
		editingId = null;
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="fixed inset-0 z-50 flex flex-col items-center justify-end pb-6 bg-black/20"
	onpointerdown={(e) => { if (e.target === e.currentTarget) onclose(); }}
>
	<div
		class="w-full max-w-5xl mx-4 bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden"
		style="max-height: 52vh"
	>
		<!-- Header -->
		<div class="flex items-center justify-between px-5 py-3 border-b border-slate-100 shrink-0">
			<div class="flex items-center gap-2">
				<svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
				</svg>
				<span class="text-sm font-semibold text-slate-700 truncate max-w-sm">
					{objectTitle || 'Untitled'}
				</span>
				<span class="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{notes.length} note{notes.length === 1 ? '' : 's'}</span>
			</div>
			<button class="text-slate-300 hover:text-slate-500 text-xl leading-none" onclick={onclose}>×</button>
		</div>

		<!-- Notes row -->
		<div class="flex-1 overflow-x-auto overflow-y-hidden p-4 min-h-0">
			{#if loading}
				<p class="text-slate-400 text-sm py-4 text-center">Loading…</p>
			{:else}
				<div class="flex gap-3 h-full items-start pb-1" style="min-width: max-content">

					<!-- Add note card (always first) -->
					<div class="note-card" style="background:#fefce8; border-color:#fde68a">
						<textarea
							class="flex-1 w-full bg-transparent resize-none text-sm text-slate-700 outline-none placeholder-amber-300 leading-relaxed"
							placeholder="New note…"
							bind:value={newContent}
							onkeydown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) addNote(); }}
						></textarea>
						<button
							onclick={addNote}
							disabled={adding || !newContent.trim()}
							class="mt-2 self-end text-xs font-semibold text-amber-500 hover:text-amber-700 disabled:opacity-40 transition-colors"
						>+ Add</button>
					</div>

					{#each notes as note (note.id)}
						{@const c = palette(note.id)}
						<div
							class="note-card group"
							style="background:{c.bg}; border-color:{c.border}"
						>
							{#if editingId === note.id}
								<textarea
									class="flex-1 w-full bg-transparent resize-none text-sm text-slate-700 outline-none leading-relaxed"
									bind:value={editingContent}
									onblur={() => saveEdit(note.id)}
									onkeydown={(e) => { if (e.key === 'Escape') editingId = null; }}
									autofocus
								></textarea>
							{:else}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<p
									class="flex-1 text-sm text-slate-700 leading-relaxed whitespace-pre-wrap break-words cursor-text select-text"
									onclick={() => startEdit(note)}
									onkeydown={(e) => e.key === 'Enter' && startEdit(note)}
								>
									{#if note.content}
										{note.content}
									{:else}
										<span class="text-slate-300 italic">Empty note</span>
									{/if}
								</p>
							{/if}

							<button
								class="absolute top-2 right-2 text-slate-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity text-base leading-none"
								onclick={() => deleteNote(note.id)}
								title="Delete"
							>×</button>
						</div>
					{/each}

					{#if notes.length === 0}
						<p class="text-slate-400 text-sm self-center px-4 italic">No notes yet — add one →</p>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.note-card {
		position: relative;
		width: 176px;
		min-height: 148px;
		flex-shrink: 0;
		border-radius: 10px;
		border-width: 1px;
		border-style: solid;
		padding: 12px;
		display: flex;
		flex-direction: column;
	}
</style>
