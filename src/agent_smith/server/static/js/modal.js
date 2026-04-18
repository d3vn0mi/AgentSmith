/* Modal system — openModal, openConfirm, closeModal. Focus trap + Esc. */
import { h, qs, icon, trapFocus } from './dom.js';

let releaseFocus = null;

export function closeModal() {
    const root = qs('#modal-root');
    if (!root) return;
    if (releaseFocus) { releaseFocus(); releaseFocus = null; }
    root.replaceChildren();
    document.body.style.overflow = '';
}

/**
 * Open a modal dialog.
 * @param {object} opts
 * @param {string} opts.title            — visible in header and used as aria-labelledby target.
 * @param {Node|Node[]} opts.body        — content for the scrollable body.
 * @param {Array<{label:string, kind?:string, onclick:(e:MouseEvent)=>void}>} [opts.actions]
 *                                       — footer buttons. Omit to hide the footer.
 * @param {boolean} [opts.closeOnBackdrop=true]
 */
export function openModal({ title, body, actions = [], closeOnBackdrop = true }) {
    const root = qs('#modal-root');
    if (!root) return;
    closeModal();

    const closeBtn = h('button', {
        class: 'btn btn-ghost btn-icon btn-sm',
        'aria-label': 'Close dialog',
        type: 'button',
        onclick: closeModal,
    }, icon('x'));

    const footer = actions.length
        ? h('div', { class: 'modal-footer' }, actions.map(a =>
            h('button', {
                class: `btn btn-${a.kind || 'primary'}`,
                type: 'button',
                onclick: a.onclick,
            }, a.label)))
        : null;

    const modal = h('div', {
        class: 'modal',
        role: 'dialog',
        'aria-modal': 'true',
        'aria-labelledby': 'modal-title',
        tabindex: '-1',
    }, [
        h('div', { class: 'modal-header' }, [
            h('div', { id: 'modal-title', class: 'modal-title' }, title),
            closeBtn,
        ]),
        h('div', { class: 'modal-body' }, body),
        footer,
    ]);

    const backdrop = h('div', {
        class: 'modal-backdrop',
        onclick: (e) => { if (closeOnBackdrop && e.target === backdrop) closeModal(); },
    }, modal);

    root.appendChild(backdrop);
    document.body.style.overflow = 'hidden';
    releaseFocus = trapFocus(modal, closeModal);
}

/**
 * Convenience for destructive confirmations. Resolves true on confirm, false on cancel/close.
 * @returns {Promise<boolean>}
 */
export function openConfirm({ title, message, confirmLabel = 'Delete', kind = 'danger' }) {
    return new Promise((resolve) => {
        openModal({
            title,
            body: h('p', null, message),
            actions: [
                { label: 'Cancel',     kind: 'ghost', onclick: () => { closeModal(); resolve(false); } },
                { label: confirmLabel, kind,          onclick: () => { closeModal(); resolve(true);  } },
            ],
        });
    });
}
