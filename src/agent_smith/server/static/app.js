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

/* ===== Missions list ===== */
ROUTES.missions = () => renderMissionsList();

async function renderMissionsList() {
    const list = document.getElementById('missions-list');
    list.replaceChildren();
    const resp = await apiRequest('/api/missions');
    if (!resp.ok) { list.appendChild(h('li', null, 'failed')); return; }
    const missions = await resp.json();
    if (missions.length === 0) {
        list.appendChild(h('li', null, 'No missions yet.'));
    } else {
        for (const m of missions) {
            const a = h('a', { href: `#mission/${m.id}` },
                `[${m.status}] ${m.name} — ${m.target} (${m.playbook})`);
            list.appendChild(h('li', null, a));
        }
    }
    document.getElementById('mission-new').onclick = openMissionCreate;
}

async function openMissionCreate() {
    const [profiles, playbooks] = await Promise.all([
        apiRequest('/api/profiles').then(r => r.json()),
        apiRequest('/api/playbooks').then(r => r.json()),
    ]);
    if (profiles.length === 0) {
        alert('Create a Kali profile first.');
        location.hash = 'profiles';
        return;
    }
    if (playbooks.length === 0) {
        alert('No playbooks on disk.');
        return;
    }

    const name = prompt('Mission name?'); if (!name) return;
    const target = prompt('Target IP/host?'); if (!target) return;
    const profileName = prompt('Kali profile?\n'
        + profiles.map(p => ` - ${p.name}`).join('\n'), profiles[0].name);
    const profile = profiles.find(p => p.name === profileName);
    if (!profile) { alert('unknown profile'); return; }
    const playbook = prompt('Playbook?\n'
        + playbooks.map(p => ` - ${p.filename}`).join('\n'),
        playbooks[0].filename);

    const resp = await apiRequest('/api/missions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, target, playbook,
                                 kali_profile_id: profile.id }),
    });
    const body = await resp.json();
    if (!resp.ok) { alert(body.detail || 'failed'); return; }
    location.hash = `mission/${body.id}`;
}

/* ===== EventBuffer — bounded, seq-keyed ===== */
class EventBuffer {
    constructor({ capacity = 500 } = {}) {
        this.capacity = capacity;
        this.items = [];
        this.seen = new Set();
    }
    get size() { return this.items.length; }
    get oldestSeq() { return this.items.length ? this.items[0].seq : null; }
    get newestSeq() {
        return this.items.length ? this.items[this.items.length - 1].seq : null;
    }
    append(ev) {
        if (this.seen.has(ev.seq)) return false;
        this.items.push(ev);
        this.seen.add(ev.seq);
        this.items.sort((a, b) => a.seq - b.seq);
        while (this.items.length > this.capacity) {
            const dropped = this.items.shift();
            this.seen.delete(dropped.seq);
        }
        return true;
    }
    prepend(list) {
        for (const ev of list) {
            if (this.seen.has(ev.seq)) continue;
            this.items.push(ev);
            this.seen.add(ev.seq);
        }
        this.items.sort((a, b) => a.seq - b.seq);
        while (this.items.length > this.capacity) {
            const dropped = this.items.pop();
            this.seen.delete(dropped.seq);
        }
    }
    clear() { this.items = []; this.seen.clear(); }
}

/* ===== Mission detail ===== */
ROUTES.mission = (id) => renderMissionDetail(id);

const detailState = {
    missionId: null,
    buffer: null,
    ws: null,
    filter: new Set(),
    autoTail: true,
    pendingNew: 0,
};

function filterKey(id) { return `filter:${id}`; }

function tearDownDetail() {
    if (detailState.ws) {
        try { detailState.ws.close(1000); } catch (_) {}
    }
    detailState.ws = null;
    detailState.buffer = null;
    detailState.missionId = null;
    detailState.autoTail = true;
    detailState.pendingNew = 0;
}

function buildLiveTab(id) {
    const tab = document.getElementById('mission-tab-live');
    tab.replaceChildren();

    const bar = h('div', { class: 'filter-bar' });
    for (const t of ['thinking', 'tool', 'evidence', 'phase', 'error']) {
        const cb = h('input', { type: 'checkbox', dataset: { filter: t } });
        cb.checked = detailState.filter.size === 0 || detailState.filter.has(t);
        cb.onchange = () => {
            detailState.filter = new Set(
                [...tab.querySelectorAll('[data-filter]')]
                    .filter(b => b.checked)
                    .map(b => b.dataset.filter));
            localStorage.setItem(
                filterKey(id), JSON.stringify([...detailState.filter]));
            renderEventList();
        };
        bar.appendChild(h('label', null, [cb, ' ' + t]));
    }
    tab.appendChild(bar);

    const list = h('div', { id: 'event-list', class: 'event-list' });
    tab.appendChild(list);

    const banner = h('div', {
        id: 'tail-banner', class: 'tail-banner', hidden: true,
        onclick: () => {
            detailState.autoTail = true;
            banner.hidden = true;
            detailState.pendingNew = 0;
            renderEventList();
            list.scrollTop = list.scrollHeight;
        },
    }, ['↓ ', h('span', { id: 'tail-count' }, '0'), ' new — click to jump']);
    tab.appendChild(banner);

    list.addEventListener('scroll', () => {
        const atBottom =
            list.scrollTop + list.clientHeight >= list.scrollHeight - 4;
        detailState.autoTail = atBottom;
        if (atBottom) {
            detailState.pendingNew = 0;
            banner.hidden = true;
        }
        if (list.scrollTop === 0) loadOlderEvents(id);
    });
}

function eventMatchesFilter(e) {
    if (detailState.filter.size === 0) return true;
    if (e.type.startsWith('agent.thinking')) return detailState.filter.has('thinking');
    if (e.type.startsWith('tool.'))           return detailState.filter.has('tool');
    if (e.type.startsWith('evidence.'))       return detailState.filter.has('evidence');
    if (e.type.startsWith('phase.'))          return detailState.filter.has('phase');
    if (e.type.includes('failed'))            return detailState.filter.has('error');
    return true;
}

function renderEventList() {
    const list = document.getElementById('event-list');
    if (!list) return;
    const items = detailState.buffer.items.filter(eventMatchesFilter);
    list.replaceChildren();
    const frag = document.createDocumentFragment();
    for (const e of items) {
        const row = h('div', {
            class: 'event-row', dataset: { seq: String(e.seq) },
            onclick: () => openEventDrawer(e),
        }, [
            h('span', { class: 'ev-ts' },
               e.ts.replace('T', ' ').replace('Z', '')),
            h('span', { class: 'ev-type' }, e.type),
            h('span', { class: 'ev-body' },
               JSON.stringify(e.data).slice(0, 160)),
        ]);
        frag.appendChild(row);
    }
    list.appendChild(frag);
    if (detailState.autoTail) list.scrollTop = list.scrollHeight;
}

async function renderMissionDetail(id) {
    if (detailState.missionId && detailState.missionId !== id) tearDownDetail();
    detailState.missionId = id;
    detailState.buffer = new EventBuffer({ capacity: 500 });
    try {
        detailState.filter = new Set(
            JSON.parse(localStorage.getItem(filterKey(id)) || '[]'));
    } catch (_) { detailState.filter = new Set(); }

    const resp = await apiRequest(`/api/missions/${id}`);
    if (!resp.ok) { alert('mission not found'); return; }
    const mission = await resp.json();
    document.getElementById('mission-title').replaceChildren(
        document.createTextNode(mission.name));
    document.getElementById('mission-header').replaceChildren(
        document.createTextNode(
            `[${mission.status}] ${mission.target} — ${mission.playbook}`));

    const tabs = ['live', 'graph', 'evidence', 'history'];
    const tabLoaders = {
        live:     () => buildLiveTab(id),
        graph:    () => (typeof loadGraphTab === 'function') && loadGraphTab(id),
        evidence: () => (typeof loadEvidenceTab === 'function') && loadEvidenceTab(id),
        history:  () => (typeof loadHistoryTab === 'function') && loadHistoryTab(id),
    };
    tabs.forEach(t => {
        const btn = document.querySelector(`#mission-tabs [data-tab="${t}"]`);
        btn.onclick = () => {
            tabs.forEach(x =>
                document.getElementById(`mission-tab-${x}`).hidden = (x !== t));
            document.querySelectorAll('#mission-tabs button[data-tab]')
                .forEach(b => b.classList.toggle('tab-active', b === btn));
            tabLoaders[t]();
        };
    });

    document.getElementById('mission-export').onclick = () => {
        window.location.href = `/api/missions/${id}/report.md`;
    };
    document.getElementById('mission-stop').onclick = () => {
        apiRequest(`/api/missions/${id}/stop`, { method: 'POST' });
    };

    buildLiveTab(id);

    const events = await (await apiRequest(
        `/api/missions/${id}/events?limit=200`)).json();
    detailState.buffer.prepend(events);
    const initialNewest = detailState.buffer.newestSeq;
    renderEventList();
    openMissionWS(id, initialNewest == null ? -1 : initialNewest);
}

async function loadOlderEvents(id) {
    if (!detailState.buffer) return;
    const oldest = detailState.buffer.oldestSeq;
    if (oldest == null || oldest === 0) return;
    const resp = await apiRequest(
        `/api/missions/${id}/events?before=${oldest}&limit=200`);
    if (!resp.ok) return;
    const older = await resp.json();
    if (older.length === 0) return;
    const asc = [...older].sort((a, b) => a.seq - b.seq);
    const list = document.getElementById('event-list');
    const prevH = list.scrollHeight;
    detailState.buffer.prepend(asc);
    renderEventList();
    list.scrollTop = list.scrollHeight - prevH;
}

function openEventDrawer(e) {
    const existing = document.getElementById('event-drawer');
    if (existing) existing.remove();
    const closeBtn = h('button', {
        onclick: (ev) => ev.currentTarget.parentElement.parentElement.remove(),
    }, '✕');
    const header = h('header', null, [
        h('strong', null, `seq ${e.seq} · ${e.type}`),
        closeBtn,
    ]);
    const pre = h('pre');
    pre.textContent = JSON.stringify(e, null, 2);
    const drawer = h('aside', { id: 'event-drawer', class: 'event-drawer' },
                     [header, pre]);
    document.body.appendChild(drawer);
}

function openMissionWS(id, sinceSeq) {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const token = encodeURIComponent(state.token);
    const url = `${proto}//${location.host}/ws/missions/${id}?since=${sinceSeq}&token=${token}`;
    const ws = new WebSocket(url);
    detailState.ws = ws;

    ws.onmessage = (m) => {
        const e = JSON.parse(m.data);
        const added = detailState.buffer.append(e);
        if (!added) return;
        if (detailState.autoTail) {
            renderEventList();
        } else {
            detailState.pendingNew++;
            const banner = document.getElementById('tail-banner');
            const count = document.getElementById('tail-count');
            if (count) count.textContent = String(detailState.pendingNew);
            if (banner) banner.hidden = false;
        }
    };

    ws.onclose = () => {
        if (detailState.missionId !== id) return;
        setTimeout(() => {
            if (detailState.missionId === id) {
                openMissionWS(id, detailState.buffer.newestSeq ?? -1);
            }
        }, 1500);
    };
    ws.onerror = () => {};
}
