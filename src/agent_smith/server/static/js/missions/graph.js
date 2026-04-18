/* Graph tab — zero-dep SVG DAG renderer. */
import { h } from '../dom.js';
import { apiRequest } from '../api.js';

const NS = 'http://www.w3.org/2000/svg';

function statusStroke(status) {
    switch (status) {
        case 'complete': return 'var(--color-state-success)';
        case 'running':  return 'var(--color-state-running)';
        case 'failed':   return 'var(--color-state-danger)';
        case 'skipped':  return 'var(--color-text-dim)';
        case 'ready':    return 'var(--color-state-info)';
        default:         return 'var(--color-border-strong)';
    }
}

/** Column-per-depth layout. Each node is 160x40, gap 200x60, pad 20. */
function renderDag(tasks) {
    const byId = new Map(tasks.map(t => [t.id, t]));
    const depth = new Map();
    function d(id) {
        if (depth.has(id)) return depth.get(id);
        const t = byId.get(id);
        const deps = (t && t.dependencies) || [];
        const v = deps.length === 0 ? 0 : 1 + Math.max(...deps.map(d));
        depth.set(id, v);
        return v;
    }
    for (const t of tasks) d(t.id);

    const columns = new Map();
    for (const t of tasks) {
        const col = depth.get(t.id);
        const c = columns.get(col) || [];
        c.push(t);
        columns.set(col, c);
    }

    const COL_W = 200, ROW_H = 60, PAD = 20;
    const colCount = columns.size;
    const maxColLen = Math.max(...[...columns.values()].map(c => c.length), 1);
    const width  = PAD * 2 + colCount * COL_W;
    const height = PAD * 2 + maxColLen * ROW_H;

    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.setAttribute('width',  String(width));
    svg.setAttribute('height', String(height));
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Mission task DAG');

    const positions = new Map();
    for (const [col, items] of columns) {
        items.forEach((t, i) => {
            positions.set(t.id, { x: PAD + col * COL_W, y: PAD + i * ROW_H });
        });
    }

    // Edges first (drawn under nodes).
    for (const t of tasks) {
        for (const dep of (t.dependencies || [])) {
            const a = positions.get(dep);
            const b = positions.get(t.id);
            if (!a || !b) continue;
            const line = document.createElementNS(NS, 'path');
            const mx = (a.x + 160 + b.x) / 2;
            line.setAttribute('d',
                `M${a.x + 160},${a.y + 20} C${mx},${a.y + 20} ${mx},${b.y + 20} ${b.x},${b.y + 20}`);
            line.setAttribute('fill',   'none');
            line.setAttribute('stroke', 'var(--color-border-strong)');
            line.setAttribute('stroke-width', '1.5');
            svg.appendChild(line);
        }
    }

    // Nodes.
    for (const t of tasks) {
        const p = positions.get(t.id);
        const g = document.createElementNS(NS, 'g');
        g.setAttribute('transform', `translate(${p.x},${p.y})`);

        const rect = document.createElementNS(NS, 'rect');
        rect.setAttribute('width', '160');
        rect.setAttribute('height', '40');
        rect.setAttribute('rx', '6');
        rect.setAttribute('fill',   'var(--color-bg-panel-raised)');
        rect.setAttribute('stroke', statusStroke(t.status));
        rect.setAttribute('stroke-width', '1.5');
        g.appendChild(rect);

        const nameEl = document.createElementNS(NS, 'text');
        nameEl.setAttribute('x', '10');
        nameEl.setAttribute('y', '16');
        nameEl.setAttribute('fill', 'var(--color-text-primary)');
        nameEl.setAttribute('font-size', '11');
        nameEl.setAttribute('font-family', 'var(--font-mono)');
        nameEl.textContent = (t.name || t.id || '').slice(0, 22);
        g.appendChild(nameEl);

        const statusEl = document.createElementNS(NS, 'text');
        statusEl.setAttribute('x', '10');
        statusEl.setAttribute('y', '32');
        statusEl.setAttribute('fill', statusStroke(t.status));
        statusEl.setAttribute('font-size', '10');
        statusEl.setAttribute('font-family', 'var(--font-mono)');
        statusEl.textContent = t.status || 'pending';
        g.appendChild(statusEl);

        svg.appendChild(g);
    }

    return svg;
}

export function buildGraphTab({ panel, missionId }) {
    (async () => {
        const resp = await apiRequest(`/api/v2/assessments/${missionId}/graph`);
        if (!resp.ok) {
            panel.replaceChildren(h('div', { class: 'empty-state' }, 'Graph not available for this mission.'));
            return;
        }
        const g = await resp.json();
        if (!g.tasks || g.tasks.length === 0) {
            panel.replaceChildren(h('div', { class: 'empty-state' },
                'No task graph yet — this playbook may not use the v2 DAG engine.'));
            return;
        }
        const summary = h('div', {
            class: 'graph-summary mono muted',
            style: { padding: 'var(--space-2) 0' },
        }, `${g.finished || 0} / ${g.total || g.tasks.length} tasks complete`);
        panel.replaceChildren(h('div', null, [summary, renderDag(g.tasks)]));
    })();
    return () => {};
}
