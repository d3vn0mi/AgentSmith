/* Timeline tab — stub. Task 16 implements the full event stream. */
import { h } from '../dom.js';
export function buildTimelineTab({ panel }) {
    panel.replaceChildren(h('div', { class: 'empty-state' }, 'Timeline — upcoming task'));
    return () => {};
}
