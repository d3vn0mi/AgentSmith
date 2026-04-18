/* Findings tab — aggregated typed view (flags / creds / ports / web / vulns). */
import { h, icon } from '../dom.js';
import { apiRequest } from '../api.js';

const CATEGORIES = [
    { key: 'flags',         title: 'Flags captured',  iconName: 'flag',     className: 'card-success' },
    { key: 'credentials',   title: 'Credentials',     iconName: 'key',      className: 'card-warn' },
    { key: 'open_ports',    title: 'Open ports',      iconName: 'activity', className: 'card-info' },
    { key: 'web_endpoints', title: 'Web endpoints',   iconName: 'target',   className: 'card-info' },
    { key: 'vulns',         title: 'Vulnerabilities', iconName: 'zap',      className: 'card-danger' },
];

function dedupe(arr) {
    const seen = new Set();
    const out = [];
    for (const x of arr) {
        const k = JSON.stringify(x);
        if (seen.has(k)) continue;
        seen.add(k);
        out.push(x);
    }
    return out;
}

function renderList(key, items) {
    if (key === 'flags') {
        return h('ul', { class: 'findings-list' },
            items.map(f => h('li', { class: 'mono' }, [
                h('span', { class: `chip chip-${f.type === 'root' ? 'danger' : 'warn'}` }, f.type || 'flag'),
                ' ',
                h('span', null, f.value || ''),
            ])));
    }
    if (key === 'open_ports') {
        return h('table', { class: 'data-table' }, [
            h('thead', null, h('tr', null, [
                h('th', null, 'Host'),
                h('th', null, 'Port'),
                h('th', null, 'Svc'),
                h('th', null, 'Version'),
            ])),
            h('tbody', null, items.map(p => h('tr', null, [
                h('td', { class: 'td-mono' }, p.host_ip || '—'),
                h('td', { class: 'td-mono' }, `${p.number}/${p.protocol || 'tcp'}`),
                h('td', null, p.service || '—'),
                h('td', { class: 'td-mono dim' }, p.version || '—'),
            ]))),
        ]);
    }
    if (key === 'web_endpoints') {
        return h('ul', { class: 'findings-list mono' },
            items.map(w => h('li', null, [
                h('span', {
                    class: `chip chip-${String(w.status).startsWith('2') ? 'success' : 'dim'}`,
                }, String(w.status || '?')),
                ' ',
                h('a', { href: w.url, target: '_blank', rel: 'noopener' }, w.url || ''),
                w.title ? h('span', { class: 'dim' }, ' — ' + w.title) : null,
            ])));
    }
    if (key === 'credentials') {
        return h('ul', { class: 'findings-list mono' },
            items.map(c => h('li', null, `${c.username || '?'}@${c.service || '?'}`)));
    }
    if (key === 'vulns') {
        return h('ul', { class: 'findings-list' },
            items.map(v => h('li', null, [
                h('span', {
                    class: `chip chip-${v.severity === 'critical' || v.severity === 'high' ? 'danger' : 'warn'}`,
                }, v.severity || '?'),
                ' ',
                h('span', null, v.title || v.cve || ''),
            ])));
    }
    const pre = h('pre', { class: 'mono' });
    pre.textContent = JSON.stringify(items, null, 2);
    return pre;
}

function buildSection({ key, title, iconName, className }, items) {
    const head = h('div', { class: 'findings-head' }, [
        icon(iconName, { className: 'icon icon-lg' }),
        h('div', { class: 'findings-title' }, title),
        h('span', { class: 'chip chip-dim' }, String(items.length)),
    ]);
    const body = items.length === 0
        ? h('div', { class: 'empty-state', style: { padding: '16px' } }, 'None yet.')
        : renderList(key, items);
    return h('div', { class: `card findings-card ${className}` }, [head, body]);
}

export function buildFindingsTab({ panel, missionId }) {
    (async () => {
        const types = 'flag_captured,evidence_updated,fact_emitted';
        const resp = await apiRequest(`/api/missions/${missionId}/events?types=${types}&limit=1000`);
        if (!resp.ok) {
            panel.replaceChildren(h('div', { class: 'error-state' }, 'Failed to load findings'));
            return;
        }
        const events = await resp.json();
        const data = { flags: [], credentials: [], open_ports: [], web_endpoints: [], vulns: [] };

        for (const e of events) {
            const d = e.data || {};
            if (e.type === 'flag_captured') {
                data.flags.push({ type: d.type, value: d.value, ts: e.ts });
            } else if (e.type === 'evidence_updated') {
                for (const key of Object.keys(data)) {
                    if (Array.isArray(d[key])) data[key].push(...d[key]);
                }
            } else if (e.type === 'fact_emitted') {
                const t = (d.type || '').toLowerCase();
                if (t === 'openport')    data.open_ports.push(d.payload || {});
                if (t === 'webendpoint') data.web_endpoints.push(d.payload || {});
            }
        }

        for (const k of Object.keys(data)) data[k] = dedupe(data[k]);

        const sections = CATEGORIES.map(cat => buildSection(cat, data[cat.key]));
        panel.replaceChildren(h('div', { class: 'findings-grid' }, sections));
    })();

    return () => {};
}
