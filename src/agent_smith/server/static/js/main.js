/* Entrypoint: register routes, bootstrap the app. */
import { auth } from './api.js';
import * as router from './router.js';
import { renderShell } from './shell.js';
import { renderLogin } from './login.js';
import { h } from './dom.js';
import './shortcuts.js';

/**
 * Gate a route renderer on a valid access token.
 *
 * On no token, calls `router.navigate('login')` which mutates `location.hash`
 * and triggers another `hashchange`-driven `route()` call. The renderer never
 * executes, so no partial UI is painted. Order of operations if the user
 * lands on an unknown hash while unauthenticated:
 *
 *   #settings → route() unknown → navigate('missions')
 *                                 → route() missions → requireAuth → navigate('login')
 *                                                                   → route() login → renderLogin
 *
 * All three hashchanges fire synchronously within the event loop tick; the
 * user sees one final render (login). Do NOT add DOM side effects to a
 * renderer before its auth check — the guard is a wrapper, not a pre-route hook.
 */
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
