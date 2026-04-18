/* Entrypoint: register routes, bootstrap the app. */
import { auth } from './api.js';
import * as router from './router.js';
import { renderShell } from './shell.js';
import { renderLogin } from './login.js';
import { h } from './dom.js';
import './shortcuts.js';

function requireAuth(fn) {
    return (...args) => {
        if (!auth.token) { router.navigate('login'); return; }
        fn(...args);
    };
}

router.register('login', renderLogin);
router.register('missions',  requireAuth(() => renderShell(h('div', { class: 'empty-state' }, 'Missions — Phase 2'))));
router.register('profiles',  requireAuth(() => renderShell(h('div', { class: 'empty-state' }, 'Profiles — Phase 2'))));
router.register('playbooks', requireAuth(() => renderShell(h('div', { class: 'empty-state' }, 'Playbooks — Phase 4'))));
router.register('mission',   requireAuth((id) => renderShell(h('div', { class: 'empty-state' }, `Mission ${id} — Phase 2`))));

document.addEventListener('DOMContentLoaded', () => router.route());
