/* Report tab — safe markdown preview + download. */
import { h, icon } from '../dom.js';
import { auth } from '../api.js';

/** Inline tokens: **bold**, `code`, [text](url). Returns array of text / Nodes. */
function inline(s) {
    const out = [];
    const re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
    let last = 0;
    let m;
    while ((m = re.exec(s)) !== null) {
        if (m.index > last) out.push(s.slice(last, m.index));
        const tok = m[0];
        if (tok.startsWith('**')) {
            out.push(h('strong', null, tok.slice(2, -2)));
        } else if (tok.startsWith('`')) {
            out.push(h('code', { class: 'mono' }, tok.slice(1, -1)));
        } else if (tok.startsWith('[')) {
            const linkM = tok.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
            if (linkM) {
                out.push(h('a', { href: linkM[2], rel: 'noopener', target: '_blank' }, linkM[1]));
            } else {
                out.push(tok);
            }
        }
        last = m.index + tok.length;
    }
    if (last < s.length) out.push(s.slice(last));
    return out;
}

/** Tiny subset: headings, fenced code, unordered lists, paragraphs with inline. */
function renderMarkdown(md) {
    const lines = md.split('\n');
    const root = h('div', { class: 'md' });
    let i = 0;
    while (i < lines.length) {
        const line = lines[i];
        if (line.startsWith('```')) {
            const fence = [];
            i++;
            while (i < lines.length && !lines[i].startsWith('```')) { fence.push(lines[i]); i++; }
            i++; // skip closing fence
            const code = h('code', null, fence.join('\n'));
            root.appendChild(h('pre', { class: 'mono' }, code));
            continue;
        }
        if (line.startsWith('#')) {
            const level = Math.min((line.match(/^#+/) || ['#'])[0].length, 6);
            root.appendChild(h('h' + level, null, line.replace(/^#+\s*/, '')));
            i++;
            continue;
        }
        if (line.trim().startsWith('- ')) {
            const list = h('ul');
            while (i < lines.length && lines[i].trim().startsWith('- ')) {
                list.appendChild(h('li', null, inline(lines[i].trim().slice(2))));
                i++;
            }
            root.appendChild(list);
            continue;
        }
        if (line.trim() === '') { i++; continue; }
        root.appendChild(h('p', null, inline(line)));
        i++;
    }
    return root;
}

export function buildReportTab({ panel, missionId }) {
    panel.replaceChildren(h('div', { class: 'empty-state' }, 'Loading report…'));
    (async () => {
        const resp = await fetch(`/api/missions/${missionId}/report.md`, {
            headers: { 'Authorization': `Bearer ${auth.token}` },
        });
        if (!resp.ok) {
            panel.replaceChildren(h('div', { class: 'error-state' }, 'Failed to load report'));
            return;
        }
        const md = await resp.text();
        const downloadBtn = h('a', {
            href: `/api/missions/${missionId}/report.md`,
            class: 'btn btn-primary btn-sm',
            download: `mission-${String(missionId).slice(0, 8)}.md`,
        }, [icon('download'), ' Download .md']);
        panel.replaceChildren(h('div', { class: 'report-wrap' }, [
            h('div', { class: 'report-toolbar' }, downloadBtn),
            renderMarkdown(md),
        ]));
    })();
    return () => {};
}
