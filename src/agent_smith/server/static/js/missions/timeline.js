/* Timeline tab — event stream with filters, keyboard nav, tail banner. */
import { h, qs, qsa } from '../dom.js';
import { apiRequest } from '../api.js';
import { openModal, closeModal } from '../modal.js';
import { toast } from '../toast.js';
import { categorize, KINDS } from '../event_types.js';
import { truncate } from '../format.js';

const FILTER_KEY = (id) => `agentsmith.timeline.filter.${id}`;

function loadFilter(id) {
    try { return new Set(JSON.parse(localStorage.getItem(FILTER_KEY(id)) || '[]')); }
    catch { return new Set(); }
}
function saveFilter(id, s) { localStorage.setItem(FILTER_KEY(id), JSON.stringify([...s])); }

function kindColorClass(kind) {
    switch (kind) {
        case 'error':    return 'danger';
        case 'finding':  return 'success';
        case 'phase':    return 'info';
        case 'evidence': return 'info';
        case 'tool':     return 'running';
        case 'thinking': return 'dim';
        case 'mission':  return 'info';
        default:         return 'dim';
    }
}

function kindChip(kind) {
    return h('span', { class: `chip chip-${kindColorClass(kind)}` }, kind);
}

/** Short human summary per event — shown in the `.tl-body` cell. */
function summary(ev) {
    const d = ev.data || {};
    const t = ev.type || '';
    if (/thinking|thought/.test(t))                return truncate(d.text || d.message || '...', 180);
    if (/command_executing|tool.*started/.test(t)) return truncate(d.command || d.cmd || '', 180);
    if (/command_executed|tool.*complete/.test(t)) {
        const exit = d.exit_code ?? d.rc ?? '?';
        return `exit=${exit} ${truncate(d.stdout_preview || '', 140)}`;
    }
    if (/flag/.test(t))          return `[${d.type || 'flag'}] ${d.value || ''}`;
    if (/phase/.test(t))         return d.phase || '';
    if (/fact/.test(t))          return `${d.type || 'fact'} ${JSON.stringify(d.payload || {}).slice(0, 140)}`;
    if (/evidence/.test(t))      return `[${d.category || '?'}] ${JSON.stringify(d.item ?? d).slice(0, 140)}`;
    if (/failed|error/.test(t))  return truncate(d.error || d.message || '', 180);
    return truncate(JSON.stringify(d), 160);
}

function renderRow(ev) {
    const { kind } = categorize(ev.type);
    const ts = (ev.ts || '').replace('T', ' ').replace('Z', '');
    return h('div', {
        class: 'tl-row',
        dataset: { seq: String(ev.seq), kind },
        tabindex: '-1',
        onclick: () => openEventDrawer(ev),
        onkeydown: (e) => { if (e.key === 'Enter') { e.preventDefault(); openEventDrawer(ev); } },
    }, [
        h('span', { class: 'tl-ts mono dim' }, ts),
        kindChip(kind),
        h('span', { class: 'tl-type mono' }, ev.type || ''),
        h('span', { class: 'tl-body' }, summary(ev)),
    ]);
}

function openEventDrawer(ev) {
    const pre = h('pre', {
        class: 'mono',
        style: { whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: '12px' },
    });
    pre.textContent = JSON.stringify(ev, null, 2);
    openModal({
        title: `seq ${ev.seq} · ${ev.type}`,
        body: h('div', null, pre),
        actions: [
            {
                label: 'Copy JSON', kind: 'ghost',
                onclick: () => {
                    navigator.clipboard.writeText(JSON.stringify(ev, null, 2));
                    toast.success('Copied');
                },
            },
            { label: 'Close', kind: 'primary', onclick: closeModal },
        ],
    });
}

export function buildTimelineTab({ panel, missionId, buffer }) {
    let autoTail = true;
    let pendingNew = 0;
    let focusedSeq = null;

    const filterBar = h('div', { class: 'tl-filters' }, KINDS.map(k => {
        const activeFilters = loadFilter(missionId);
        const cb = h('input', { type: 'checkbox', dataset: { filter: k } });
        cb.checked = activeFilters.size === 0 || activeFilters.has(k);
        cb.onchange = () => {
            const s = new Set(
                qsa('[data-filter]', filterBar).filter(x => x.checked).map(x => x.dataset.filter)
            );
            saveFilter(missionId, s);
            rerender();
        };
        return h('label', { class: 'checkbox-row' }, [cb, kindChip(k)]);
    }));

    const list = h('div', {
        class: 'tl-list',
        id: 'tl-list',
        role: 'log',
        'aria-live': 'off',
    });

    const banner = h('button', {
        class: 'tl-banner',
        hidden: true,
        type: 'button',
        onclick: () => jumpToLatest(),
    }, ['↓ ', h('span', { id: 'tl-banner-count' }, '0'), ' new — click to jump']);

    panel.replaceChildren(h('div', { class: 'tl-wrap' }, [filterBar, list, banner]));

    function rerender() {
        const filters = loadFilter(missionId);
        const visible = buffer.items.filter(e => {
            if (filters.size === 0) return true;
            return filters.has(categorize(e.type).kind);
        });
        const frag = document.createDocumentFragment();
        for (const e of visible) frag.appendChild(renderRow(e));
        list.replaceChildren(frag);
        if (autoTail) list.scrollTop = list.scrollHeight;
    }

    function jumpToLatest() {
        autoTail = true; pendingNew = 0; banner.hidden = true;
        rerender();
        list.scrollTop = list.scrollHeight;
    }

    list.addEventListener('scroll', () => {
        const atBottom = list.scrollTop + list.clientHeight >= list.scrollHeight - 4;
        autoTail = atBottom;
        if (atBottom) { pendingNew = 0; banner.hidden = true; }
        if (list.scrollTop === 0) loadOlder();
    });

    async function loadOlder() {
        const oldest = buffer.oldestSeq;
        if (oldest == null || oldest === 0) return;
        const resp = await apiRequest(`/api/missions/${missionId}/events?before=${oldest}&limit=200`);
        if (!resp.ok) return;
        const older = await resp.json();
        if (older.length === 0) return;
        const prev = list.scrollHeight;
        buffer.prepend([...older].sort((a, b) => a.seq - b.seq));
        rerender();
        list.scrollTop = list.scrollHeight - prev;
    }

    // Panel-scoped keyboard nav: j/k/End/Enter.
    panel.addEventListener('keydown', (e) => {
        if (!(panel.contains(document.activeElement) || document.activeElement === document.body)) return;
        const rows = qsa('.tl-row', list);
        if (rows.length === 0) return;
        if (e.key === 'j' || e.key === 'k') {
            e.preventDefault();
            let idx = rows.findIndex(r => Number(r.dataset.seq) === focusedSeq);
            if (idx < 0) idx = e.key === 'j' ? 0 : rows.length - 1;
            else idx = Math.max(0, Math.min(rows.length - 1, idx + (e.key === 'j' ? 1 : -1)));
            rows.forEach(r => r.classList.remove('tl-focus'));
            rows[idx].classList.add('tl-focus');
            rows[idx].focus();
            rows[idx].scrollIntoView({ block: 'nearest' });
            focusedSeq = Number(rows[idx].dataset.seq);
        } else if (e.key === 'End') {
            e.preventDefault();
            jumpToLatest();
        }
    });

    rerender();

    // onEvent handler invoked by detail.js for each new WS message.
    return (_ev) => {
        if (autoTail) {
            rerender();
        } else {
            pendingNew++;
            const countEl = qs('#tl-banner-count');
            if (countEl) countEl.textContent = String(pendingNew);
            banner.hidden = false;
        }
    };
}
