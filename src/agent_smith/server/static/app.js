/* AgentSmith - Puppet Master Dashboard Logic */

const state = {
    token: localStorage.getItem('agentsmith_token') || '',
    refreshToken: localStorage.getItem('agentsmith_refresh') || '',
    role: localStorage.getItem('agentsmith_role') || '',
    ws: null,
    paused: false,
    cmdCount: 0,
    startTime: null,
    timerInterval: null,
};

/* ===== Auth ===== */

async function apiRequest(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    const resp = await fetch(url, { ...options, headers });

    if (resp.status === 401 && state.refreshToken) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            headers['Authorization'] = `Bearer ${state.token}`;
            return fetch(url, { ...options, headers });
        }
    }
    return resp;
}

async function refreshAccessToken() {
    try {
        const resp = await fetch('/api/auth/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: state.refreshToken }),
        });
        if (resp.ok) {
            const data = await resp.json();
            state.token = data.access_token;
            state.refreshToken = data.refresh_token;
            localStorage.setItem('agentsmith_token', data.access_token);
            localStorage.setItem('agentsmith_refresh', data.refresh_token);
            return true;
        }
    } catch (e) {}
    logout();
    return false;
}

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorEl = document.getElementById('login-error');
    errorEl.hidden = true;

    try {
        const form = new URLSearchParams();
        form.append('username', username);
        form.append('password', password);

        const resp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: form,
        });

        if (resp.ok) {
            const data = await resp.json();
            state.token = data.access_token;
            state.refreshToken = data.refresh_token;
            state.role = data.role;
            localStorage.setItem('agentsmith_token', data.access_token);
            localStorage.setItem('agentsmith_refresh', data.refresh_token);
            localStorage.setItem('agentsmith_role', data.role);
            showDashboard();
        } else {
            const err = await resp.json();
            errorEl.textContent = err.detail || 'Login failed';
            errorEl.hidden = false;
        }
    } catch (err) {
        errorEl.textContent = 'Connection error';
        errorEl.hidden = false;
    }
});

function logout() {
    state.token = '';
    state.refreshToken = '';
    state.role = '';
    localStorage.removeItem('agentsmith_token');
    localStorage.removeItem('agentsmith_refresh');
    localStorage.removeItem('agentsmith_role');
    location.hash = '';
    route();
}

/* ===== DOM helper — no innerHTML, ever ===== */
function h(tag, attrs, children) {
    const el = document.createElement(tag);
    if (attrs) {
        for (const [k, v] of Object.entries(attrs)) {
            if (k === 'class') el.className = v;
            else if (k === 'dataset') Object.assign(el.dataset, v);
            else if (k.startsWith('on')) el[k.toLowerCase()] = v;
            else if (k === 'hidden') { if (v) el.hidden = true; }
            else if (v !== undefined && v !== null) el.setAttribute(k, v);
        }
    }
    if (children != null) {
        const kids = Array.isArray(children) ? children : [children];
        for (const c of kids) {
            if (c == null) continue;
            el.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
        }
    }
    return el;
}

/* ===== Router ===== */
const ROUTES = {};

function parseHash() {
    const raw = location.hash.slice(1) || 'missions';
    const [name, ...rest] = raw.split('/');
    return { name, args: rest };
}

function showPage(page) {
    ['profiles', 'missions', 'mission-detail'].forEach(p => {
        const el = document.getElementById('page-' + p);
        if (el) el.hidden = (p !== page);
    });
}

function route() {
    if (!state.token) { showLogin(); return; }
    document.getElementById('login-screen').hidden = true;
    document.getElementById('sidenav').hidden = false;
    document.getElementById('app').hidden = false;
    const { name, args } = parseHash();
    if (name === 'mission' && args[0]) {
        showPage('mission-detail');
        ROUTES.mission && ROUTES.mission(args[0]);
    } else if (ROUTES[name]) {
        showPage(name);
        ROUTES[name]();
    } else {
        location.hash = 'missions';
    }
}

function showLogin() {
    document.getElementById('login-screen').hidden = false;
    document.getElementById('sidenav').hidden = true;
    document.getElementById('app').hidden = true;
}

window.addEventListener('hashchange', route);
window.addEventListener('DOMContentLoaded', route);

function showDashboard() {
    location.hash = 'missions';
    route();
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('logout-btn');
    if (btn) btn.addEventListener('click', () => logout());
});

/* ===== Profiles page ===== */
ROUTES.profiles = () => renderProfiles();

async function renderProfiles() {
    const list = document.getElementById('profiles-list');
    list.replaceChildren();
    const resp = await apiRequest('/api/profiles');
    if (!resp.ok) { list.appendChild(h('li', null, 'failed to load')); return; }
    const profiles = await resp.json();
    if (profiles.length === 0) {
        list.appendChild(h('li', null, 'No profiles yet.'));
    } else {
        for (const p of profiles) {
            const del = h('button', { onclick: () => deleteProfile(p.id) }, 'delete');
            const li = h('li', null, [
                `${p.name} — ${p.username}@${p.host}:${p.port} (${p.auth_type}) `,
                del,
            ]);
            list.appendChild(li);
        }
    }
    document.getElementById('profile-add').onclick = openProfileModal;
}

async function deleteProfile(id) {
    if (!confirm('Delete this profile?')) return;
    const resp = await apiRequest(`/api/profiles/${id}`, { method: 'DELETE' });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        alert(err.detail || 'delete failed');
        return;
    }
    renderProfiles();
}

function openProfileModal() {
    const name = prompt('Profile name?'); if (!name) return;
    const host = prompt('Host?'); if (!host) return;
    const port = parseInt(prompt('Port (22)?', '22'), 10);
    const username = prompt('Username?'); if (!username) return;
    const auth_type = prompt('Auth type (key or password)?', 'key');
    const credential = prompt(
        auth_type === 'key'
            ? 'Paste the SSH private key (full PEM):'
            : 'Password:');
    if (!credential) return;

    apiRequest('/api/profiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, host, port, username, auth_type, credential }),
    }).then(r => r.json().then(body => {
        if (!r.ok) alert(body.detail || 'create failed');
        else renderProfiles();
    }));
}
