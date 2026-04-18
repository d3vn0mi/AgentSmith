/* Evidence tab — stub. Task 18 implements the typed rendering. */
import { h } from '../dom.js';
export function buildEvidenceTab({ panel }) {
    panel.replaceChildren(h('div', { class: 'empty-state' }, 'Evidence — upcoming task'));
    return () => {};
}
