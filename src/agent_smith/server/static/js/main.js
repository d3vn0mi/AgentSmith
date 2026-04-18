/* Entrypoint: register routes, bootstrap the app. */
import { auth } from './api.js';
import * as router from './router.js';
import { renderShell } from './shell.js';
import { renderLogin } from './login.js';
import { renderMissionList } from './missions/list.js';
import { renderMissionDetail } from './missions/detail.js';
import { renderProfiles } from './profiles.js';
import { renderPlaybooks } from './playbooks.js';
import { h } from './dom.js';
import * as sc from './shortcuts.js';

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
router.register('missions', requireAuth(() => renderMissionList()));
router.register('profiles',  requireAuth(() => renderProfiles()));
router.register('playbooks', requireAuth(() => renderPlaybooks()));
router.register('mission', requireAuth((id) => renderMissionDetail(id)));

sc.register('m', () => router.navigate('missions'),  { label: 'Go to Missions',  group: 'navigation' });
sc.register('p', () => router.navigate('profiles'),  { label: 'Go to Profiles',  group: 'navigation' });
sc.register('b', () => router.navigate('playbooks'), { label: 'Go to Playbooks', group: 'navigation' });

document.addEventListener('DOMContentLoaded', () => router.route());
