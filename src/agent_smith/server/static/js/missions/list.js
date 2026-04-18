/* Missions fleet view — polling table. */
import { h, qs, icon } from '../dom.js';
import { apiRequest } from '../api.js';
import { toast } from '../toast.js';
import { truncate, rel } from '../format.js';
import { renderShell } from '../shell.js';
import { openNewMissionModal } from './new_mission.js';

const POLL_MS = 5000;
let pollTimer = null;

const STATUS_META = {
    running:  { cls: 'chip-running', label: 'running', live: true },
    complete: { cls: 'chip-success', label: 'complete' },
    failed:   { cls: 'chip-danger',  label: 'failed' },
    stopped:  { cls: 'chip-warn',    label: 'stopped' },
    created:  { cls: 'chip-dim',     label: 'created' },
};

function statusChip(status) {
    const m = STATUS_META[status] || { cls: 'chip-dim', label: String(status || 'unknown') };
    return h('span', { class: `chip ${m.cls}` }, [
        m.live ? h('span', { class: 'live-dot', 'aria-hidden': 'true' }) : null,
        m.label,
    ]);
}

function renderRow(m) {
    return h('tr', null, [
        h('td', null, statusChip(m.status)),
        h('td', null, m.name),
        h('td', { class: 'td-mono' }, truncate(m.target, 40)),
        h('td', { class: 'td-mono' }, m.playbook),
        h('td', { class: 'td-mono dim' }, m.started_at ? rel(m.started_at) : '—'),
        h('td', { class: 'td-mono dim' }, '—'),
        h('td', { class: 'td-mono dim' }, '—'),
        h('td', { class: 'td-actions' },
            h('a', {
                href: `#mission/${m.id}`,
                class: 'btn btn-sm btn-ghost',
                'aria-label': `Open mission ${m.name}`,
            }, 'Open')),
    ]);
}

function renderEmpty() {
    return h('div', { class: 'empty-state' }, [
        h('p', null, 'No missions yet.'),
        h('button', {
            class: 'btn btn-primary',
            type: 'button',
            onclick: openNewMissionModal,
            style: { marginTop: '12px' },
        }, [icon('plus'), ' Start a mission']),
    ]);
}

function renderSkeletonRows() {
    const rows = [];
    for (let i = 0; i < 3; i++) {
        rows.push(h('tr', null, [
            h('td', null, h('span', { class: 'skeleton' })),
            h('td', null, h('span', { class: 'skeleton', style: { width: '10em' } })),
            h('td', null, h('span', { class: 'skeleton', style: { width: '8em' } })),
            h('td', null, h('span', { class: 'skeleton', style: { width: '6em' } })),
            h('td', null, h('span', { class: 'skeleton', style: { width: '4em' } })),
            h('td', null, h('span', { class: 'skeleton', style: { width: '3em' } })),
            h('td', null, h('span', { class: 'skeleton', style: { width: '4em' } })),
            h('td', null, null),
        ]));
    }
    return rows;
}

function buildTableShell(tbody) {
    return h('div', { class: 'panel' }, [
        h('table', { class: 'data-table' }, [
            h('thead', null, h('tr', null, [
                h('th', null, 'Status'),
                h('th', null, 'Name'),
                h('th', null, 'Target'),
                h('th', null, 'Playbook'),
                h('th', null, 'Started'),
                h('th', null, 'Iter'),
                h('th', null, 'Cost'),
                h('th', null, ''),
            ])),
            tbody,
        ]),
    ]);
}

async function refresh(tbody, wrap) {
    const resp = await apiRequest('/api/missions');
    if (!resp.ok) {
        toast.error('Failed to load missions');
        wrap.replaceChildren(h('div', { class: 'error-state' }, 'Failed to load missions.'));
        return;
    }
    const missions = await resp.json();
    if (missions.length === 0) {
        wrap.replaceChildren(renderEmpty());
        return;
    }
    if (!tbody.isConnected) wrap.replaceChildren(buildTableShell(tbody));
    tbody.replaceChildren(...missions.map(renderRow));
}

export function renderMissionList() {
    const header = h('div', { class: 'page-header' }, [
        h('h1', null, 'Missions'),
        h('div', { class: 'page-actions' },
            h('button', {
                class: 'btn btn-primary',
                type: 'button',
                onclick: openNewMissionModal,
            }, [icon('plus'), ' New mission'])),
    ]);

    const tbody = h('tbody', null, renderSkeletonRows());
    const wrap  = h('div', null, buildTableShell(tbody));
    renderShell(h('div', { class: 'page fleet' }, [header, wrap]));

    refresh(tbody, wrap);
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(() => {
        if (!qs('.fleet')) {
            clearInterval(pollTimer);
            pollTimer = null;
            return;
        }
        refresh(tbody, wrap);
    }, POLL_MS);
}
