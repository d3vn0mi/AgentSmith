/* Toast system — aria-live notifications. */
import { h, qs, icon } from './dom.js';

const ICON_MAP = {
    success: 'check',
    error:   'alert',
    warn:    'alert',
    info:    'activity',
};

function show(message, kind = 'info', { timeout = 4000 } = {}) {
    const root = qs('#toast-root');
    if (!root) return;
    const el = h('div', {
        class: `toast toast-${kind}`,
        role: kind === 'error' ? 'alert' : 'status',
    }, [
        icon(ICON_MAP[kind] || 'activity', { className: 'icon' }),
        h('span', null, message),
    ]);
    root.appendChild(el);
    if (timeout > 0) setTimeout(() => el.remove(), timeout);
    return el;
}

export const toast = {
    success: (m, o) => show(m, 'success', o),
    error:   (m, o) => show(m, 'error',   { timeout: 6000, ...(o || {}) }),
    warn:    (m, o) => show(m, 'warn',    o),
    info:    (m, o) => show(m, 'info',    o),
};
