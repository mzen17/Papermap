<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';

	let { data, selected }: { data: Record<string, any>; selected: boolean } = $props();
</script>

<Handle type="target" position={Position.Left} />
<Handle type="source" position={Position.Right} />

<div
	class="paper-node bg-white rounded-xl shadow-md border overflow-visible w-52 cursor-default select-none transition-shadow"
	class:border-blue-400={selected}
	class:shadow-lg={selected}
	style:border-color={selected ? '#60a5fa' : '#e2e8f0'}
>
	<div class="h-1 bg-blue-500 rounded-t-xl"></div>
	<div class="p-3">
		<p class="font-semibold text-slate-800 text-sm leading-snug mb-1 break-words">
			{data.title || 'Untitled Paper'}
		</p>
		{#if data.link}
			<a
				href={data.link}
				target="_blank"
				rel="noopener noreferrer"
				class="text-blue-500 text-xs hover:underline block truncate mb-1"
			>
				{data.link}
			</a>
		{/if}
		{#if data.tags?.length}
			<div class="flex flex-wrap gap-1 mt-1">
				{#each data.tags as tag}
					<span class="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full border border-blue-100">
						{tag}
					</span>
				{/each}
			</div>
		{/if}

		<!-- Notes button -->
		<div class="flex justify-end mt-2">
			<button
				class="notes-btn flex items-center gap-1 text-slate-400 hover:text-amber-500 transition-colors"
				onclick={(e) => { e.stopPropagation(); data.onOpenNotes?.(data.id); }}
				title="Notes"
			>
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
				</svg>
				{#if data.noteCount > 0}
					<span class="text-xs font-semibold text-amber-500">{data.noteCount}</span>
				{/if}
			</button>
		</div>
	</div>
</div>

<style>
	.notes-btn {
		padding: 2px 4px;
		border-radius: 4px;
		cursor: pointer;
		background: none;
		border: none;
	}
	.notes-btn:hover {
		background: #fef3c7;
	}
</style>
