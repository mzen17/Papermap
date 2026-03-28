<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="min-h-screen bg-gray-50 flex flex-col">
	<header class="bg-slate-900 text-white px-6 py-3 flex items-center gap-3 shrink-0">
		<a href="/" class="text-lg font-semibold tracking-tight hover:text-slate-300 transition-colors">
			Papermap
		</a>
	</header>
	<main class="flex-1 flex flex-col">
		{@render children()}
	</main>
</div>
