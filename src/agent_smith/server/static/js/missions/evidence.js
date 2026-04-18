/* Evidence tab — typed rendering grouped by category. */
import { h } from '../dom.js';
import { apiRequest } from '../api.js';

function itemLine(category, item) {
    if (item == null) return String(item);
    if (category === 'hosts')
        return `${item.ip || ''}${item.hostname ? ` (${item.hostname})` : ''}${item.os ? ` — ${item.os}` : ''}`;
    if (category === 'open_ports')
        return `${item.host_ip || ''}:${item.number}/${item.protocol || 'tcp'}${item.service ? ` ${item.service}` : ''}${item.version ? ` ${item.version}` : ''}`;
    if (category === 'web_endpoints')
        return `${item.url || ''}${item.status != null ? ` → ${item.status}` : ''}${item.title ? ` ${item.title}` : ''}`;
    if (category === 'credentials')
        return `${item.username || '?'}:${item.password ? '●●●●' : ''}${item.service ? `@${item.service}` : ''}`;
    if (category === 'vulns')
        return `[${item.severity || '?'}] ${item.title || item.cve || ''}`;
    if (category === 'flags')
        return `[${item.type || 'flag'}] ${item.value || ''}`;
    return typeof item === 'string' ? item : JSON.stringify(item);
}

function dedupeStringify(items) {
    const seen = new Set();
    const out = [];
    for (const i of items) {
        const k = JSON.stringify(i);
        if (seen.has(k)) continue;
        seen.add(k);
        out.push(i);
    }
    return out;
}

export function buildEvidenceTab({ panel, missionId }) {
    (async () => {
        const types = 'evidence_updated,evidence.added,fact_emitted';
        const resp = await apiRequest(`/api/missions/${missionId}/events?types=${types}&limit=1000`);
        if (!resp.ok) {
            panel.replaceChildren(h('div', { class: 'error-state' }, 'Failed to load evidence'));
            return;
        }
        const events = await resp.json();
        if (events.length === 0) {
            panel.replaceChildren(h('div', { class: 'empty-state' }, 'No evidence collected yet.'));
            return;
        }

        const bucket = new Map();
        for (const e of events) {
            const d = e.data || {};
            if (e.type === 'evidence_updated') {
                for (const [cat, list] of Object.entries(d)) {
                    if (!Array.isArray(list)) continue;
                    if (!bucket.has(cat)) bucket.set(cat, []);
                    for (const item of list) bucket.get(cat).push(item);
                }
            } else if (e.type === 'evidence.added') {
                const cat = d.category || 'other';
                if (!bucket.has(cat)) bucket.set(cat, []);
                bucket.get(cat).push(d.item);
            } else if (e.type === 'fact_emitted') {
                const cat = (d.type || 'fact').toLowerCase();
                if (!bucket.has(cat)) bucket.set(cat, []);
                bucket.get(cat).push(d.payload || d);
            }
        }

        const sections = [];
        for (const [cat, items] of bucket) {
            const uniq = dedupeStringify(items);
            sections.push(h('div', { class: 'ev-section' }, [
                h('div', { class: 'ev-section-head' }, [
                    h('span', { class: 'ev-section-title' }, cat),
                    h('span', { class: 'chip chip-dim' }, String(uniq.length)),
                ]),
                h('ul', { class: 'ev-list mono' },
                    uniq.map(it => h('li', null, itemLine(cat, it)))),
            ]));
        }
        panel.replaceChildren(h('div', { class: 'ev-grid' }, sections));
    })();

    return () => {};
}
