/**
 * Categorize raw event type strings into UI-level kinds.
 * The agent emits a mix of dot-style and underscore-style names; we substring-match.
 */
const RULES = [
    { kind: 'error',    re: /failed|error/i,           color: 'danger'  },
    { kind: 'finding',  re: /flag/i,                   color: 'success' },
    { kind: 'phase',    re: /phase/i,                  color: 'info'    },
    { kind: 'evidence', re: /evidence|fact/i,          color: 'info'    },
    { kind: 'tool',     re: /tool|command/i,           color: 'running' },
    { kind: 'thinking', re: /thinking|thought|think/i, color: 'dim'     },
    { kind: 'mission',  re: /mission/i,                color: 'info'    },
];

export function categorize(type) {
    if (!type) return { kind: 'other', color: 'dim' };
    for (const r of RULES) if (r.re.test(type)) return { kind: r.kind, color: r.color };
    return { kind: 'other', color: 'dim' };
}

export const KINDS = ['thinking', 'tool', 'evidence', 'finding', 'phase', 'mission', 'error', 'other'];
