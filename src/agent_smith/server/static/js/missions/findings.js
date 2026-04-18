/* Findings tab — stub. Task 19 implements the aggregated view. */
import { h } from '../dom.js';
export function buildFindingsTab({ panel }) {
    panel.replaceChildren(h('div', { class: 'empty-state' }, 'Findings — upcoming task'));
    return () => {};
}
