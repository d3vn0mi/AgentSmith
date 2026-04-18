/* Graph tab — stub. Task 20 implements the SVG DAG. */
import { h } from '../dom.js';
export function buildGraphTab({ panel }) {
    panel.replaceChildren(h('div', { class: 'empty-state' }, 'Graph — upcoming task'));
    return () => {};
}
