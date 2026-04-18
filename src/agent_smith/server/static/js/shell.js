/* App shell: left rail + topbar + main surface. */
import { h, qs, icon } from './dom.js';
import { auth, clearAuth } from './api.js';
import { navigate } from './router.js';

const NAV = [
    { hash: 'missions',  label: 'Missions',  icon: 'crosshair' },
    { hash: 'profiles',  label: 'Profiles',  icon: 'key' },
    { hash: 'playbooks', label: 'Playbooks', icon: 'book-open' },
];

function currentHash() {
    return (location.hash.slice(1) || 'missions').split('/')[0];
}

export function renderShell(content) {
    const root = qs('#app-root');
    if (!root) return;
    root.replaceChildren();

    const rail = h('nav', { id: 'rail', 'aria-label': 'Main navigation' }, [
        h('div', { class: 'rail-logo', title: 'AgentSmith' }, 'AS'),
        ...NAV.map(n => {
            const active = currentHash() === n.hash;
            return h('a', {
                href: `#${n.hash}`,
                class: 'rail-item' + (active ? ' active' : ''),
                'aria-current': active ? 'page' : null,
                'aria-label': n.label,
            }, [icon(n.icon, { className: 'icon icon-lg' }), h('span', null, n.label)]);
        }),
        h('div', { style: { flex: '1' } }),
        h('button', {
            class: 'rail-item',
            type: 'button',
            'aria-label': 'Log out',
            onclick: () => { clearAuth(); navigate('login'); },
        }, [icon('log-out', { className: 'icon icon-lg' }), h('span', null, 'Logout')]),
    ]);

    const topbar = h('header', { id: 'topbar' }, [
        h('div', { class: 'topbar-title' }, 'AgentSmith'),
        h('div', { class: 'topbar-right' }, [
            auth.username ? h('span', { class: 'dim', style: { fontSize: '12px' } }, auth.username) : null,
            h('button', {
                class: 'btn btn-ghost btn-icon btn-sm',
                type: 'button',
                'aria-label': 'Keyboard shortcuts',
                onclick: () => document.dispatchEvent(new KeyboardEvent('keydown', { key: '?' })),
            }, icon('keyboard')),
        ]),
    ]);

    const main = h('main', { id: 'surface', tabindex: '-1' }, content || null);

    root.appendChild(h('div', { id: 'app-grid' }, [rail, topbar, main]));
}
