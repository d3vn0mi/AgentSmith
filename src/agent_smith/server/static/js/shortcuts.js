/* Keyboard shortcut registry + ? overlay. */
import { h } from './dom.js';
import { openModal, closeModal } from './modal.js';

/** Map<key, {fn, label, group}>. `key` is matched against `event.key`. */
const registry = new Map();

/**
 * Register a keyboard shortcut.
 * @param {string} key          — matched against event.key. Single letters are case-sensitive.
 * @param {(e: KeyboardEvent) => void} fn
 * @param {object} [opts]
 * @param {string} [opts.label] — human-readable description for the overlay.
 * @param {string} [opts.group='global']
 * @returns {() => void} teardown — unregister the shortcut.
 */
export function register(key, fn, { label, group = 'global' } = {}) {
    registry.set(key, { fn, label: label || key, group });
    return () => registry.delete(key);
}

function inTextEntry(e) {
    const t = e.target;
    return t instanceof HTMLInputElement
        || t instanceof HTMLTextAreaElement
        || t instanceof HTMLSelectElement
        || (t instanceof HTMLElement && t.isContentEditable);
}

document.addEventListener('keydown', (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (inTextEntry(e)) return;
    const entry = registry.get(e.key);
    if (!entry) return;
    e.preventDefault();
    entry.fn(e);
});

function openShortcutOverlay() {
    const groups = new Map();
    for (const [key, entry] of registry.entries()) {
        if (!groups.has(entry.group)) groups.set(entry.group, []);
        groups.get(entry.group).push({ key, label: entry.label });
    }
    const body = [];
    for (const [group, items] of groups) {
        body.push(h('h4', {
            class: 'dim',
            style: { marginTop: '12px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' },
        }, group));
        const list = h('div', {
            style: { display: 'grid', gridTemplateColumns: 'max-content 1fr', gap: '6px 16px' },
        });
        for (const { key, label } of items) {
            list.appendChild(h('kbd', { class: 'chip' }, key));
            list.appendChild(h('span', null, label));
        }
        body.push(list);
    }
    openModal({
        title: 'Keyboard shortcuts',
        body,
        actions: [{ label: 'Close', kind: 'primary', onclick: closeModal }],
    });
}

register('?', openShortcutOverlay, { label: 'Show keyboard shortcuts', group: 'global' });
