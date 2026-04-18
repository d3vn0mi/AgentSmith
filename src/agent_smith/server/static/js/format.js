/** mm:ss (or HH:MM:SS for >=1h) elapsed from ms. */
export function elapsed(ms) {
    const s = Math.max(0, Math.floor(ms / 1000));
    const hh = Math.floor(s / 3600);
    const mm = Math.floor((s % 3600) / 60);
    const ss = s % 60;
    const pad = (n) => String(n).padStart(2, '0');
    return hh > 0 ? `${pad(hh)}:${pad(mm)}:${pad(ss)}` : `${pad(mm)}:${pad(ss)}`;
}

/** Truncate string to `n` chars, replacing the last char with ellipsis when over. */
export function truncate(s, n) {
    if (s == null) return '';
    s = String(s);
    return s.length <= n ? s : s.slice(0, n - 1) + '\u2026';
}

/** Format a number as USD, or em-dash for null/undefined. */
export function usd(n) {
    if (n == null) return '\u2014';
    return '$' + Number(n).toFixed(2);
}

/** Relative time: "3s ago", "4m ago", "2h ago". Reads Date.now() and new Date(ts). */
export function rel(ts) {
    const sec = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (sec < 60)    return `${sec}s ago`;
    if (sec < 3600)  return `${Math.floor(sec / 60)}m ago`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
    return `${Math.floor(sec / 86400)}d ago`;
}
