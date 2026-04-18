/* Login page. */
import { h, qs } from './dom.js';
import { login } from './api.js';
import { navigate } from './router.js';

export function renderLogin() {
    const root = qs('#app-root');
    if (!root) return;
    root.replaceChildren();

    const error = h('p', { class: 'error-msg', role: 'alert', hidden: true });

    const form = h('form', {
        class: 'login-form',
        onsubmit: async (e) => {
            e.preventDefault();
            error.hidden = true;
            const user = form.querySelector('[name=username]').value;
            const pass = form.querySelector('[name=password]').value;
            try {
                await login(user, pass);
                navigate('missions');
            } catch (err) {
                error.textContent = err.message || 'Login failed';
                error.hidden = false;
            }
        },
    }, [
        h('h1', { class: 'login-title' }, 'AgentSmith'),
        h('p', { class: 'login-subtitle dim' }, 'Puppet Master control plane'),
        h('div', { class: 'field' }, [
            h('label', { for: 'l-user' }, 'Username'),
            h('input', { id: 'l-user', name: 'username', class: 'input', required: true, autocomplete: 'username' }),
        ]),
        h('div', { class: 'field' }, [
            h('label', { for: 'l-pass' }, 'Password'),
            h('input', { id: 'l-pass', name: 'password', class: 'input', type: 'password', required: true, autocomplete: 'current-password' }),
        ]),
        h('button', { class: 'btn btn-primary', type: 'submit', style: { width: '100%' } }, 'Sign in'),
        error,
    ]);

    root.appendChild(h('div', { class: 'login-shell' }, form));
}
