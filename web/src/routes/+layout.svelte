<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import type { User } from '$lib/types';
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
	let user = $state<User | null>(null);
	let checked = $state(false);

	onMount(async () => {
		if ($page.url.pathname.startsWith('/login')) {
			checked = true;
			return;
		}
		try {
			user = await api.me();
			checked = true;
		} catch {
			goto('/login');
		}
	});

	async function logout() {
		await api.logout();
		window.location.href = '/login';
	}
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

{#if $page.url.pathname.startsWith('/login')}
	{@render children()}
{:else if !checked}
	<div class="min-h-screen bg-gray-50 flex items-center justify-center">
		<p class="text-slate-400 text-sm">Loading…</p>
	</div>
{:else}
	<div class="min-h-screen bg-gray-50 flex flex-col">
		<header class="bg-slate-900 text-white px-6 py-3 flex items-center gap-3 shrink-0">
			<a href="/" class="text-lg font-semibold tracking-tight hover:text-slate-300 transition-colors">
				Papermap
			</a>
			{#if user}
				<div class="ml-auto flex items-center gap-4">
					<span class="text-sm text-slate-400">{user.username}</span>
					<button
						onclick={logout}
						class="text-sm text-slate-400 hover:text-white transition-colors"
					>
						Sign out
					</button>
				</div>
			{/if}
		</header>
		<main class="flex-1 flex flex-col">
			{@render children()}
		</main>
	</div>
{/if}
