/* Report tab — stub. Task 21 implements the markdown preview. */
import { h } from '../dom.js';
export function buildReportTab({ panel }) {
    panel.replaceChildren(h('div', { class: 'empty-state' }, 'Report — upcoming task'));
    return () => {};
}
