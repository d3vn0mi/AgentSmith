/** Bounded, seq-keyed, sorted event buffer. */
export class EventBuffer {
    constructor({ capacity = 500 } = {}) {
        this.capacity = capacity;
        this.items = [];
        this.seen = new Set();
    }

    get size()      { return this.items.length; }
    get oldestSeq() { return this.items.length ? this.items[0].seq : null; }
    get newestSeq() { return this.items.length ? this.items[this.items.length - 1].seq : null; }

    append(ev) {
        if (this.seen.has(ev.seq)) return false;
        this.items.push(ev);
        this.seen.add(ev.seq);
        this.items.sort((a, b) => a.seq - b.seq);
        while (this.items.length > this.capacity) {
            const dropped = this.items.shift();
            this.seen.delete(dropped.seq);
        }
        return true;
    }

    prepend(list) {
        for (const ev of list) {
            if (this.seen.has(ev.seq)) continue;
            this.items.push(ev);
            this.seen.add(ev.seq);
        }
        this.items.sort((a, b) => a.seq - b.seq);
        while (this.items.length > this.capacity) {
            const dropped = this.items.pop();
            this.seen.delete(dropped.seq);
        }
    }

    clear() {
        this.items = [];
        this.seen.clear();
    }
}
