/* DOM helpers - no innerHTML, focus-trap, aria-live announce. */

const ICON_PATHS = {
    'crosshair':     ['M22 12h-4', 'M6 12H2', 'M12 6V2', 'M12 22v-4', 'M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12Z'],
    'key':           ['M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777Zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4'],
    'book-open':     ['M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2zM22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'],
    'log-out':       ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'M16 17l5-5-5-5', 'M21 12H9'],
    'plus':          ['M5 12h14', 'M12 5v14'],
    'x':             ['M18 6 6 18', 'M6 6l12 12'],
    'check':         ['M20 6 9 17l-5-5'],
    'alert':         ['M12 9v4', 'M12 17h.01', 'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z'],
    'chevron-right': ['m9 18 6-6-6-6'],
    'chevron-down':  ['m6 9 6 6 6-6'],
    'trash':         ['M3 6h18', 'M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6', 'M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2'],
    'square':        ['M3 3h18v18H3z'],
    'download':      ['M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4', 'M7 10l5 5 5-5', 'M12 15V3'],
    'keyboard':      ['M6 8h.01', 'M10 8h.01', 'M14 8h.01', 'M18 8h.01', 'M8 12h.01', 'M12 12h.01', 'M16 12h.01', 'M7 16h10', 'M2 4h20a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z'],
    'search':        ['m21 21-4.3-4.3', 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z'],
    'refresh':       ['M3 12a9 9 0 0 1 15-6.7L21 8', 'M21 3v5h-5', 'M21 12a9 9 0 0 1-15 6.7L3 16', 'M3 21v-5h5'],
    'activity':      ['M22 12h-4l-3 9L9 3l-3 9H2'],
    'target':        ['M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z', 'M18 12a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z', 'M14 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z'],
    'flag':          ['M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z', 'M4 22v-7'],
    'zap':           ['M13 2 3 14h9l-1 8 10-12h-9l1-8z'],
};

/**
 * DOM element factory. Never uses innerHTML.
 * @param {string} tag
 * @param {Object|null} [attrs]
 * @param {Node|string|number|Array|null} [children]
 * @returns {HTMLElement}
 */
export function h(tag, attrs, children) {
    const el = document.createElement(tag);
    if (attrs) {
        for (const [k, v] of Object.entries(attrs)) {
            if (v === undefined || v === null || v === false) continue;
            if (k === 'class') {
                el.className = v;
            } else if (k === 'dataset') {
                Object.assign(el.dataset, v);
            } else if (k === 'style') {
                Object.assign(el.style, v);
            } else if (k.startsWith('on')) {
                el[k.toLowerCase()] = v;
            } else if (k === 'hidden') {
                el.hidden = !!v;
            } else if (v === true) {
                el.setAttribute(k, '');
            } else {
                el.setAttribute(k, v);
            }
        }
    }
    if (children != null) {
        const kids = Array.isArray(children) ? children : [children];
        for (const c of kids) {
            if (c === null || c === undefined || c === false) continue;
            if (typeof c === 'string' || typeof c === 'number') {
                el.appendChild(document.createTextNode(String(c)));
            } else {
                el.appendChild(c);
            }
        }
    }
    return el;
}

/**
 * @param {string} sel
 * @param {Document|Element} [root=document]
 * @returns {Element|null}
 */
export function qs(sel, root = document) {
    return root.querySelector(sel);
}

/**
 * @param {string} sel
 * @param {Document|Element} [root=document]
 * @returns {Element[]}
 */
export function qsa(sel, root = document) {
    return [...root.querySelectorAll(sel)];
}

const SVG_NS = 'http://www.w3.org/2000/svg';

/**
 * Build a Lucide SVG icon element.
 * @param {string} name
 * @param {{ size?: number, className?: string }} [opts]
 * @returns {SVGElement|HTMLElement}
 */
export function icon(name, { size = 16, className = 'icon' } = {}) {
    const paths = ICON_PATHS[name];
    if (!paths) {
        return h('span', { class: className });
    }
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('width', size);
    svg.setAttribute('height', size);
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '1.5');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('class', className);
    svg.setAttribute('aria-hidden', 'true');
    for (const d of paths) {
        const path = document.createElementNS(SVG_NS, 'path');
        path.setAttribute('d', d);
        svg.appendChild(path);
    }
    return svg;
}

const FOCUSABLE_SELECTOR = [
    'a[href]',
    'button:not(:disabled)',
    'textarea:not(:disabled)',
    'input:not(:disabled)',
    'select:not(:disabled)',
    '[tabindex]:not([tabindex="-1"])',
].join(', ');

/**
 * Trap keyboard focus inside `container`. Intended for modals/dialogs.
 *
 * Returns a teardown function. The caller is responsible for calling teardown
 * exactly once when the trap should end (e.g., when the modal closes). Failing
 * to call teardown will leak the keydown listener and the saved focus target.
 *
 * Do NOT call trapFocus twice on the same container without calling the first
 * teardown — both listeners would stack. openModal/closeModal in modal.js
 * enforces this by always calling closeModal (which invokes the prior teardown)
 * before opening a new modal.
 */
export function trapFocus(container, onEscape) {
    const focusables = () => qsa(FOCUSABLE_SELECTOR, container);
    const previouslyFocused = document.activeElement;

    function handler(e) {
        if (e.key === 'Escape') {
            e.preventDefault();
            onEscape?.();
            return;
        }
        if (e.key !== 'Tab') return;

        const items = focusables();
        if (!items.length) {
            e.preventDefault();
            return;
        }
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey) {
            if (document.activeElement === first) {
                e.preventDefault();
                last.focus();
            }
        } else {
            if (document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
    }

    container.addEventListener('keydown', handler);

    const items = focusables();
    if (items.length) {
        items[0].focus();
    } else {
        container.focus();
    }

    return function teardown() {
        container.removeEventListener('keydown', handler);
        if (previouslyFocused instanceof HTMLElement) {
            previouslyFocused.focus();
        }
    };
}

/**
 * Announce `text` to assistive technologies via the live region at #toast-root.
 *
 * Requires #toast-root to exist and be configured as an ARIA live region
 * (index.html sets role="region" aria-live="polite"). The announcement span
 * is removed after 2s to avoid stale DOM. Silently no-ops if #toast-root
 * is absent (e.g., on the login screen before shell mount).
 */
export function announceLive(text) {
    const root = qs('#toast-root');
    if (!root) return;
    const span = h('span', { class: 'sr-only' }, text);
    root.appendChild(span);
    setTimeout(() => span.remove(), 2000);
}

/**
 * Returns a debounced version of fn that fires after ms of inactivity.
 * @param {Function} fn
 * @param {number} ms
 * @returns {Function}
 */
export function debounce(fn, ms) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), ms);
    };
}
