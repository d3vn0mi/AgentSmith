/* API client — auth state, fetch wrapper with 401-refresh, WebSocket helper. */

export const auth = {
    token:        localStorage.getItem('agentsmith_token')    || '',
    refreshToken: localStorage.getItem('agentsmith_refresh')  || '',
    role:         localStorage.getItem('agentsmith_role')     || '',
    username:     localStorage.getItem('agentsmith_username') || '',
};

function saveAuth() {
    localStorage.setItem('agentsmith_token',    auth.token);
    localStorage.setItem('agentsmith_refresh',  auth.refreshToken);
    localStorage.setItem('agentsmith_role',     auth.role);
    localStorage.setItem('agentsmith_username', auth.username);
}

export function clearAuth() {
    auth.token = '';
    auth.refreshToken = '';
    auth.role = '';
    auth.username = '';
    localStorage.removeItem('agentsmith_token');
    localStorage.removeItem('agentsmith_refresh');
    localStorage.removeItem('agentsmith_role');
    localStorage.removeItem('agentsmith_username');
}

export async function apiRequest(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (auth.token) headers['Authorization'] = `Bearer ${auth.token}`;
    let resp = await fetch(url, { ...options, headers });
    if (resp.status === 401 && auth.refreshToken) {
        if (await refreshAccessToken()) {
            headers['Authorization'] = `Bearer ${auth.token}`;
            resp = await fetch(url, { ...options, headers });
        }
    }
    return resp;
}

export async function login(username, password) {
    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);
    const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form,
    });
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Login failed');
    }
    const data = await resp.json();
    auth.token        = data.access_token;
    auth.refreshToken = data.refresh_token;
    auth.role         = data.role;
    auth.username     = username;
    saveAuth();
    return data;
}

async function refreshAccessToken() {
    try {
        const resp = await fetch('/api/auth/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: auth.refreshToken }),
        });
        if (!resp.ok) { clearAuth(); return false; }
        const data = await resp.json();
        auth.token        = data.access_token;
        auth.refreshToken = data.refresh_token;
        saveAuth();
        return true;
    } catch {
        clearAuth();
        return false;
    }
}

export function openWebSocket(path, { since = -1 } = {}) {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const token = encodeURIComponent(auth.token);
    return new WebSocket(`${proto}//${location.host}${path}?since=${since}&token=${token}`);
}
