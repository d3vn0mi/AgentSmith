/* Commands tab — table of executed commands, with copy action. */
import { h } from '../dom.js';
import { apiRequest } from '../api.js';
import { toast } from '../toast.js';
import { truncate } from '../format.js';

function exitChip(code) {
    const c = Number(code);
    if (Number.isNaN(c)) return h('span', { class: 'chip chip-dim' }, '?');
    if (c === 0) return h('span', { class: 'chip chip-success' }, '0');
    return h('span', { class: 'chip chip-danger' }, String(c));
}

export function buildCommandsTab({ panel, missionId }) {
    const tbody = h('tbody');
    const table = h('div', { class: 'panel' },
        h('table', { class: 'data-table' }, [
            h('thead', null, h('tr', null, [
                h('th', null, 'When'),
                h('th', null, 'Tool'),
                h('th', null, 'Exit'),
                h('th', null, 'Command'),
                h('th', null, ''),
            ])),
            tbody,
        ]));
    panel.replaceChildren(table);

    (async () => {
        const types = 'command_executed,tool.run_complete,tool_run_complete';
        const resp = await apiRequest(`/api/missions/${missionId}/events?types=${types}&limit=1000`);
        if (!resp.ok) {
            panel.replaceChildren(h('div', { class: 'error-state' }, 'Failed to load commands'));
            return;
        }
        const rows = await resp.json();
        if (rows.length === 0) {
            panel.replaceChildren(h('div', { class: 'empty-state' }, 'No commands yet.'));
            return;
        }
        for (const e of rows) {
            const d = e.data || {};
            const cmd = d.command || d.cmd || '';
            tbody.appendChild(h('tr', null, [
                h('td', { class: 'td-mono dim' }, (e.ts || '').replace('T', ' ').replace('Z', '')),
                h('td', { class: 'td-mono' }, d.tool || '—'),
                h('td', null, exitChip(d.exit_code ?? d.rc)),
                h('td', { class: 'td-mono' }, truncate(cmd, 100)),
                h('td', { class: 'td-actions' },
                    h('button', {
                        class: 'btn btn-sm btn-ghost',
                        type: 'button',
                        'aria-label': 'Copy command',
                        onclick: () => {
                            navigator.clipboard.writeText(cmd);
                            toast.success('Copied');
                        },
                    }, 'Copy')),
            ]));
        }
    })();

    return () => { /* no live updates for commands tab */ };
}
