/* Playbooks catalog page. */
import { h, icon } from './dom.js';
import { apiRequest } from './api.js';
import { toast } from './toast.js';
import { renderShell } from './shell.js';

export async function renderPlaybooks() {
    const header = h('div', { class: 'page-header' },
        h('h1', null, 'Playbooks'));

    renderShell(h('div', { class: 'page' }, [
        header,
        h('div', { class: 'empty-state' }, 'Loading…'),
    ]));

    const resp = await apiRequest('/api/playbooks');
    if (!resp.ok) {
        toast.error('Failed to load playbooks');
        renderShell(h('div', { class: 'page' }, [
            header,
            h('div', { class: 'error-state' }, 'Failed to load'),
        ]));
        return;
    }
    const playbooks = await resp.json();

    const body = playbooks.length === 0
        ? h('div', { class: 'empty-state' }, 'No playbooks found on disk.')
        : h('div', { class: 'playbook-grid' },
            playbooks.map(p => h('div', { class: 'card playbook-card' }, [
                h('div', { class: 'playbook-head' }, [
                    icon('book-open', { className: 'icon icon-lg' }),
                    h('div', { class: 'playbook-title' }, p.name || p.filename),
                ]),
                h('p', { class: 'muted' }, p.description || 'No description.'),
                h('div', { class: 'playbook-phases' },
                    (p.phases || []).map(ph => h('span', { class: 'chip chip-dim' }, ph))),
                h('div', { class: 'playbook-file mono dim' }, p.filename),
            ])));

    renderShell(h('div', { class: 'page' }, [header, body]));
}
