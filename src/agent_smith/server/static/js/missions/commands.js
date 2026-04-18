/* Commands tab — stub. Task 17 implements the table view. */
import { h } from '../dom.js';
export function buildCommandsTab({ panel }) {
    panel.replaceChildren(h('div', { class: 'empty-state' }, 'Commands — upcoming task'));
    return () => {};
}
