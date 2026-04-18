/* Hash router. */
const routes = new Map();

export function register(name, renderFn) {
    routes.set(name, renderFn);
}

export function navigate(hash) {
    if (location.hash !== '#' + hash) location.hash = hash;
    else route();
}

function parseHash() {
    const raw = location.hash.slice(1) || 'missions';
    const [name, ...args] = raw.split('/');
    return { name, args };
}

export function route() {
    const { name, args } = parseHash();
    const renderer = routes.get(name);
    if (!renderer) { navigate('missions'); return; }
    renderer(...args);
    const surface = document.getElementById('surface');
    if (surface) surface.focus({ preventScroll: true });
}

window.addEventListener('hashchange', route);
