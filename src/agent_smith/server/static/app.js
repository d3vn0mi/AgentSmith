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
    if (state.ws) state.ws.close();
    document.getElementById('login-screen').hidden = false;
    document.getElementById('dashboard').hidden = true;
}

/* ===== Dashboard ===== */

async function showDashboard() {
    document.getElementById('login-screen').hidden = true;
    document.getElementById('dashboard').hidden = false;
    document.getElementById('user-info').textContent = `[${state.role}]`;

    connectWebSocket();
    loadInitialState();
    startTimer();
}

function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws?token=${encodeURIComponent(state.token)}`;
    state.ws = new WebSocket(wsUrl);

    state.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleEvent(msg);
    };

    state.ws.onclose = () => {
        setTimeout(connectWebSocket, 3000);
    };

    state.ws.onerror = () => {};
}

async function loadInitialState() {
    try {
        const [missionResp, evidenceResp, historyResp] = await Promise.all([
            apiRequest('/api/mission'),
            apiRequest('/api/evidence'),
            apiRequest('/api/history?limit=100'),
        ]);

        if (missionResp.ok) {
            const mission = await missionResp.json();
            updateMission(mission);
        }

        if (evidenceResp.ok) {
            const evidence = await evidenceResp.json();
            updateEvidence(evidence);
        }

        if (historyResp.ok) {
            const history = await historyResp.json();
            const log = document.getElementById('command-log');
            log.innerHTML = '';
            history.forEach(entry => addCommandEntry(entry));
        }
    } catch (e) {
        console.error('Failed to load initial state:', e);
    }
}

/* ===== Event Handlers ===== */

function handleEvent(msg) {
    switch (msg.type) {
        case 'command_executed':
            addCommandEntry({
                iteration: msg.data.iteration,
                tool_name: msg.data.tool,
                tool_args: msg.data.args,
                output: msg.data.output,
                thinking: msg.data.thinking || '',
                timestamp: msg.timestamp,
                success: msg.data.success,
            });
            break;

        case 'command_executing':
            addCommandEntry({
                iteration: msg.data.iteration,
                tool_name: msg.data.tool,
                tool_args: msg.data.args,
                output: '[Executing...]',
                thinking: msg.data.thinking || '',
                timestamp: msg.timestamp,
                executing: true,
            });
            break;

        case 'thought':
        case 'thinking':
            document.getElementById('thinking-text').textContent =
                msg.data.thinking || 'Processing...';
            break;

        case 'evidence_updated':
            updateEvidence(msg.data);
            break;

        case 'phase_changed':
            updatePhase(msg.data.phase);
            break;

        case 'flag_captured':
            showFlagNotification(msg.data.type, msg.data.value);
            break;

        case 'mission_complete':
            document.getElementById('thinking-text').textContent =
                'MISSION COMPLETE! Both flags captured.';
            updatePhase('complete');
            break;

        case 'mission_started':
            document.getElementById('target-display').textContent =
                `Target: ${msg.data.target_ip}`;
            state.startTime = Date.now();
            break;
    }
}

/* ===== UI Updates ===== */

function addCommandEntry(entry) {
    const log = document.getElementById('command-log');
    const id = `cmd-${entry.iteration}`;

    // Update existing entry if it exists (executing -> completed)
    const existing = document.getElementById(id);
    if (existing) {
        existing.remove();
    }

    const time = new Date(entry.timestamp * 1000).toLocaleTimeString();
    const success = entry.executing ? '' : (entry.success !== false ? 'success' : 'failure');
    const statusText = entry.executing ? 'RUNNING' : (entry.success !== false ? 'OK' : 'FAIL');

    const argsStr = typeof entry.tool_args === 'object'
        ? JSON.stringify(entry.tool_args, null, 0)
        : entry.tool_args || '';

    const el = document.createElement('div');
    el.className = 'cmd-entry';
    el.id = id;
    el.innerHTML = `
        <div class="cmd-header" onclick="this.parentElement.classList.toggle('expanded')">
            <span class="cmd-step">#${entry.iteration}</span>
            <span class="cmd-tool">${entry.tool_name}</span>
            <span class="cmd-status ${success}">${statusText}</span>
            <span class="cmd-time">${time}</span>
        </div>
        ${entry.thinking ? `<div class="cmd-thinking">${escapeHtml(entry.thinking).substring(0, 200)}</div>` : ''}
        <div class="cmd-output">${escapeHtml(entry.output || '')}</div>
    `;

    log.appendChild(el);
    log.scrollTop = log.scrollHeight;

    state.cmdCount++;
    document.getElementById('cmd-count').textContent = state.cmdCount;
}

function updateMission(mission) {
    updatePhase(mission.current_phase);
    document.getElementById('target-display').textContent = `Target: ${mission.target_ip}`;
    document.getElementById('iteration-display').textContent =
        `Step: ${mission.iteration}/${mission.max_iterations}`;
    state.paused = mission.paused;
    document.getElementById('pause-btn').textContent = mission.paused ? 'Resume' : 'Pause';
}

function updatePhase(phase) {
    const badge = document.getElementById('phase-badge');
    badge.textContent = phase.toUpperCase().replace('_', ' ');
    badge.className = `badge ${phase}`;
}

function updateEvidence(evidence) {
    // Flags
    const flagsEl = document.getElementById('flags-list');
    if (Object.keys(evidence.flags).length > 0) {
        flagsEl.innerHTML = Object.entries(evidence.flags)
            .map(([type, val]) => `<div class="evidence-item flag-item">${type}: ${escapeHtml(val)}</div>`)
            .join('');
    }

    // Ports
    const portsEl = document.getElementById('ports-list');
    if (evidence.ports && evidence.ports.length > 0) {
        portsEl.innerHTML = evidence.ports
            .map(p => `<div class="evidence-item port-item">${p.number}/${p.protocol} ${p.service}${p.version ? ' - ' + escapeHtml(p.version) : ''}</div>`)
            .join('');
    }

    // Credentials
    const credsEl = document.getElementById('creds-list');
    if (evidence.credentials && evidence.credentials.length > 0) {
        credsEl.innerHTML = evidence.credentials
            .map(c => `<div class="evidence-item cred-item">${escapeHtml(c.username)} (${escapeHtml(c.context)}) [${c.source}]</div>`)
            .join('');
    }

    // Vulnerabilities
    const vulnsEl = document.getElementById('vulns-list');
    if (evidence.vulnerabilities && evidence.vulnerabilities.length > 0) {
        vulnsEl.innerHTML = evidence.vulnerabilities
            .map(v => `<div class="evidence-item vuln-item">[${v.severity}] ${escapeHtml(v.name)} on ${escapeHtml(v.service)}</div>`)
            .join('');
    }

    // Files
    const filesEl = document.getElementById('files-list');
    if (evidence.files_of_interest && evidence.files_of_interest.length > 0) {
        filesEl.innerHTML = evidence.files_of_interest
            .map(f => `<div class="evidence-item">${escapeHtml(f)}</div>`)
            .join('');
    }
}

function showFlagNotification(type, value) {
    const label = type === 'user' ? 'USER FLAG' : 'ROOT FLAG';
    const thinkingEl = document.getElementById('thinking-text');
    thinkingEl.textContent = `${label} CAPTURED: ${value}`;
    thinkingEl.style.color = '#22c55e';
    setTimeout(() => { thinkingEl.style.color = ''; }, 10000);
}

/* ===== Controls ===== */

async function togglePause() {
    state.paused = !state.paused;
    const action = state.paused ? 'pause' : 'resume';
    await apiRequest('/api/control', {
        method: 'POST',
        body: JSON.stringify({ action }),
    });
    document.getElementById('pause-btn').textContent = state.paused ? 'Resume' : 'Pause';
    document.getElementById('pause-btn').className = state.paused ? 'btn btn-primary' : 'btn btn-warning';
}

async function injectCommand() {
    const tool = document.getElementById('inject-tool').value;
    const input = document.getElementById('inject-input').value;
    let args;
    try {
        args = JSON.parse(input);
    } catch (e) {
        // Treat as a shell command if JSON parsing fails
        args = { command: input };
    }

    await apiRequest('/api/control', {
        method: 'POST',
        body: JSON.stringify({ action: 'inject', tool_name: tool, tool_args: args }),
    });

    document.getElementById('inject-input').value = '';
}

/* ===== Timer ===== */

function startTimer() {
    state.startTime = state.startTime || Date.now();
    state.timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
        const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
        const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
        const s = String(elapsed % 60).padStart(2, '0');
        document.getElementById('elapsed-timer').textContent = `${h}:${m}:${s}`;
    }, 1000);
}

/* ===== Utils ===== */

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/* ===== Init ===== */

if (state.token) {
    // Try to restore session
    showDashboard();
}
