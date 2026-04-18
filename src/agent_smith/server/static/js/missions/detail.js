/* Mission detail: sticky header, ARIA tablist, WS wiring. */
import { h, qs, icon, announceLive } from '../dom.js';
import { apiRequest, openWebSocket } from '../api.js';
import { toast } from '../toast.js';
import { openConfirm } from '../modal.js';
import { navigate } from '../router.js';
import { renderShell } from '../shell.js';
import { EventBuffer } from '../event_buffer.js';
import { elapsed, usd } from '../format.js';

import { buildTimelineTab } from './timeline.js';
import { buildCommandsTab } from './commands.js';
import { buildEvidenceTab } from './evidence.js';
import { buildFindingsTab } from './findings.js';
import { buildGraphTab }    from './graph.js';
import { buildReportTab }   from './report.js';

const TABS = [
    { id: 'timeline', label: 'Timeline', build: buildTimelineTab },
    { id: 'graph',    label: 'Graph',    build: buildGraphTab },
    { id: 'findings', label: 'Findings', build: buildFindingsTab },
    { id: 'evidence', label: 'Evidence', build: buildEvidenceTab },
    { id: 'commands', label: 'Commands', build: buildCommandsTab },
    { id: 'report',   label: 'Report',   build: buildReportTab },
];

/** Per-detail-view state. Exported so tab modules can inspect it if needed. */
export const state = {
    missionId: null,
    mission: null,
    buffer: null,
    ws: null,
    phase: null,
    iteration: 0,
    cost: null,
    startedAt: null,
    timerId: null,
    activeTab: 'timeline',
    onActiveTabEvent: null,
};

function tearDown() {
    if (state.ws)      { try { state.ws.close(1000); } catch { /* ignore */ } state.ws = null; }
    if (state.timerId) { clearInterval(state.timerId); state.timerId = null; }
    state.missionId = null;
    state.mission = null;
    state.buffer = null;
    state.phase = null;
    state.iteration = 0;
    state.cost = null;
    state.startedAt = null;
    state.onActiveTabEvent = null;
}

function phaseChip(phase) {
    const map = {
        recon:        { cls: 'phase-recon',    label: 'recon' },
        enumeration:  { cls: 'phase-enum',     label: 'enum' },
        exploitation: { cls: 'phase-exploit',  label: 'exploit' },
        privesc:      { cls: 'phase-privesc',  label: 'privesc' },
        post_exploit: { cls: 'phase-post',     label: 'post' },
        complete:     { cls: 'phase-complete', label: 'complete' },
    };
    const m = map[phase] || { cls: 'chip-dim', label: phase || '—' };
    return h('span', { class: `chip ${m.cls}` }, m.label);
}

function statCell(label, valueEl) {
    return h('div', { class: 'mh-stat' }, [
        h('span', { class: 'mh-stat-label' }, label),
        valueEl,
    ]);
}

async function confirmStop() {
    const ok = await openConfirm({
        title: 'Stop mission?',
        message: 'The agent container will be killed. Collected evidence is preserved.',
        confirmLabel: 'Stop mission',
    });
    if (!ok) return;
    const resp = await apiRequest(`/api/missions/${state.missionId}/stop`, { method: 'POST' });
    if (!resp.ok) { toast.error('Stop failed'); return; }
    toast.success('Stop requested');
}

function renderHeader() {
    const inner = qs('#mission-header-inner');
    if (!inner || !state.mission) return;
    const m = state.mission;
    const running = m.status === 'running';
    inner.replaceChildren(
        h('div', { class: 'mh-title' }, [
            h('a', { href: '#missions', class: 'btn btn-ghost btn-sm' }, '← Missions'),
            h('h1', null, m.name),
            phaseChip(state.phase),
            h('span', { class: running ? 'chip chip-running' : 'chip chip-dim' }, [
                running ? h('span', { class: 'live-dot', 'aria-hidden': 'true' }) : null,
                m.status,
            ]),
        ]),
        h('div', { class: 'mh-actions' }, [
            h('button', {
                class: 'btn btn-ghost btn-sm',
                type: 'button',
                onclick: () => { window.location.href = `/api/missions/${m.id}/report.md`; },
            }, [icon('download'), ' Export .md']),
            running
                ? h('button', { class: 'btn btn-danger btn-sm', type: 'button', onclick: confirmStop },
                    [icon('square'), ' Stop'])
                : null,
        ]),
        h('div', { class: 'mh-stats' }, [
            statCell('Target',   h('span', { class: 'mono' }, m.target)),
            statCell('Playbook', h('span', { class: 'mono dim' }, m.playbook)),
            statCell('Elapsed',  h('span', { class: 'mono', id: 'mh-elapsed' }, '--:--')),
            statCell('Iter',     h('span', { class: 'mono', id: 'mh-iter' }, String(state.iteration))),
            statCell('Cost',     h('span', { class: 'mono dim', id: 'mh-cost' }, usd(state.cost))),
        ]),
    );
}

function startTimer() {
    if (state.timerId) clearInterval(state.timerId);
    state.timerId = setInterval(() => {
        const el = qs('#mh-elapsed');
        if (!el || !state.startedAt) return;
        el.textContent = elapsed(Date.now() - new Date(state.startedAt).getTime());
    }, 1000);
}

function applyEvent(ev) {
    const t = ev.type || '';
    if (t.includes('phase')) {
        const p = ev.data?.phase;
        if (p && p !== state.phase) {
            state.phase = p;
            announceLive(`phase changed to ${p}`);
            renderHeader();
        }
    }
    if (t.includes('iteration') || typeof ev.data?.iteration === 'number') {
        if (typeof ev.data?.iteration === 'number') {
            state.iteration = ev.data.iteration;
            const el = qs('#mh-iter');
            if (el) el.textContent = String(state.iteration);
        }
    }
    const costIncrement = ev.data?.cost_usd ?? ev.data?.usd;
    if (costIncrement != null) {
        state.cost = (state.cost || 0) + Number(costIncrement);
        const el = qs('#mh-cost');
        if (el) el.textContent = usd(state.cost);
    }
}

function selectTab(id) {
    state.activeTab = id;
    for (const t of TABS) {
        const btn   = qs(`#mtab-${t.id}`);
        const panel = qs(`#mpanel-${t.id}`);
        if (btn) {
            btn.setAttribute('aria-selected', String(t.id === id));
            btn.tabIndex = (t.id === id) ? 0 : -1;
        }
        if (panel) panel.hidden = (t.id !== id);
    }
    const panel = qs(`#mpanel-${id}`);
    const tab = TABS.find(x => x.id === id);
    if (panel && tab) {
        const ret = tab.build({ panel, missionId: state.missionId, buffer: state.buffer });
        state.onActiveTabEvent = (typeof ret === 'function') ? ret : null;
    }
}

function openWS(sinceSeq) {
    const ws = openWebSocket(`/ws/missions/${state.missionId}`, { since: sinceSeq });
    state.ws = ws;
    ws.onmessage = (m) => {
        let ev;
        try { ev = JSON.parse(m.data); } catch { return; }
        const added = state.buffer.append(ev);
        if (!added) return;
        applyEvent(ev);
        state.onActiveTabEvent?.(ev);
    };
    ws.onclose = () => {
        if (!state.missionId) return;
        setTimeout(() => {
            if (state.missionId) openWS(state.buffer.newestSeq ?? -1);
        }, 1500);
    };
    ws.onerror = () => { /* swallow; onclose will drive reconnect */ };
}

export async function renderMissionDetail(id) {
    if (state.missionId && state.missionId !== id) tearDown();
    state.missionId = id;
    state.buffer = new EventBuffer({ capacity: 500 });

    const resp = await apiRequest(`/api/missions/${id}`);
    if (!resp.ok) {
        toast.error('Mission not found');
        navigate('missions');
        return;
    }
    state.mission = await resp.json();
    state.startedAt = state.mission.started_at || state.mission.created_at;

    const tabBar = h('div', {
        class: 'tablist',
        role: 'tablist',
        'aria-label': 'Mission detail sections',
    }, TABS.map(t => h('button', {
        id: `mtab-${t.id}`,
        role: 'tab',
        type: 'button',
        'aria-selected': t.id === 'timeline' ? 'true' : 'false',
        'aria-controls': `mpanel-${t.id}`,
        tabindex: t.id === 'timeline' ? '0' : '-1',
        onclick: () => selectTab(t.id),
    }, t.label)));

    const panels = TABS.map(t => h('div', {
        id: `mpanel-${t.id}`,
        role: 'tabpanel',
        'aria-labelledby': `mtab-${t.id}`,
        tabindex: '0',
        hidden: t.id !== 'timeline',
        class: 'tabpanel',
    }));

    const headerShell = h('header', { id: 'mission-header', class: 'mission-header' },
        h('div', { id: 'mission-header-inner' }));

    renderShell(h('div', { class: 'mission-detail' }, [headerShell, tabBar, ...panels]));
    renderHeader();
    startTimer();

    // Initial page of events — derive phase/iter/cost.
    const histResp = await apiRequest(`/api/missions/${id}/events?limit=200`);
    if (histResp.ok) {
        const events = await histResp.json();
        state.buffer.prepend(events);
        for (const ev of events) applyEvent(ev);
        renderHeader();
    }
    selectTab('timeline');
    openWS(state.buffer.newestSeq ?? -1);
}
