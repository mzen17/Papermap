<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';

	let { data, selected }: { data: Record<string, any>; selected: boolean } = $props();
</script>

<Handle type="target" position={Position.Left} />
<Handle type="source" position={Position.Right} />

<div
	class="text-node bg-amber-50 rounded-lg px-3 py-2 w-44 cursor-default select-none transition-shadow border"
	class:shadow-md={selected}
	style:border-color={selected ? '#60a5fa' : '#fcd34d'}
>
	<p class="text-slate-700 text-sm leading-snug break-words italic">
		{data.text || 'Text'}
	</p>
</div>
