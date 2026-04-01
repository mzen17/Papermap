<script lang="ts">
	import { BASE } from '$lib/api';

	let mode = $state<'login' | 'register'>('login');
	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function submit() {
		if (!username.trim() || !password) return;
		loading = true;
		error = '';
		const endpoint = mode === 'login' ? '/auth/login' : '/auth/register';
		try {
			const res = await fetch(BASE + endpoint, {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username: username.trim(), password }),
			});
			if (res.ok) {
				window.location.href = '/';
				return;
			}
			const body = await res.json().catch(() => ({}));
			error = body.detail ?? (mode === 'login' ? 'Invalid credentials.' : 'Registration failed.');
		} catch {
			error = 'Network error. Please try again.';
		}
		loading = false;
	}

	function switchMode(m: 'login' | 'register') {
		mode = m;
		error = '';
	}
</script>

<div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
	<div class="bg-white border border-slate-200 rounded-2xl shadow-sm p-8 w-full max-w-sm">
		<div class="mb-6">
			<h1 class="text-xl font-bold text-slate-800">Papermap</h1>
			<p class="text-slate-500 text-sm mt-1">
				{mode === 'login' ? 'Sign in to continue.' : 'Create a new account.'}
			</p>
		</div>

		<form onsubmit={(e) => { e.preventDefault(); submit(); }} class="space-y-4">
			<div>
				<label class="block text-sm font-medium text-slate-700 mb-1" for="username">
					Username
				</label>
				<input
					id="username"
					type="text"
					bind:value={username}
					autocomplete={mode === 'login' ? 'username' : 'username'}
					class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
					placeholder="username"
					autofocus
				/>
			</div>
			<div>
				<label class="block text-sm font-medium text-slate-700 mb-1" for="password">
					Password
				</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					autocomplete={mode === 'login' ? 'current-password' : 'new-password'}
					class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
					placeholder="••••••••"
				/>
			</div>

			{#if error}
				<p class="text-red-500 text-sm">{error}</p>
			{/if}

			<button
				type="submit"
				disabled={loading || !username.trim() || !password}
				class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2 rounded-lg text-sm font-medium transition-colors"
			>
				{loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
			</button>
		</form>

		<p class="text-center text-sm text-slate-400 mt-5">
			{#if mode === 'login'}
				No account?
				<button onclick={() => switchMode('register')} class="text-blue-600 hover:underline">
					Register
				</button>
			{:else}
				Have an account?
				<button onclick={() => switchMode('login')} class="text-blue-600 hover:underline">
					Sign in
				</button>
			{/if}
		</p>
	</div>
</div>
