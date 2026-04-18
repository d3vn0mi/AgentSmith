import { test } from 'node:test';
import assert from 'node:assert/strict';
import { EventBuffer } from '../../src/agent_smith/server/static/js/event_buffer.js';

test('append adds events and keeps them sorted by seq', () => {
    const b = new EventBuffer({ capacity: 10 });
    assert.equal(b.append({ seq: 2 }), true);
    assert.equal(b.append({ seq: 1 }), true);
    assert.deepEqual(b.items.map(e => e.seq), [1, 2]);
});

test('append dedupes by seq', () => {
    const b = new EventBuffer({ capacity: 10 });
    b.append({ seq: 1 });
    assert.equal(b.append({ seq: 1 }), false);
    assert.equal(b.items.length, 1);
});

test('capacity drops oldest on overflow', () => {
    const b = new EventBuffer({ capacity: 3 });
    for (let i = 1; i <= 5; i++) b.append({ seq: i });
    assert.deepEqual(b.items.map(e => e.seq), [3, 4, 5]);
});

test('prepend merges older events and trims newest on overflow', () => {
    const b = new EventBuffer({ capacity: 3 });
    b.append({ seq: 5 }); b.append({ seq: 6 });
    b.prepend([{ seq: 3 }, { seq: 4 }]);
    assert.deepEqual(b.items.map(e => e.seq), [3, 4, 5]);
});

test('oldestSeq / newestSeq reflect the window', () => {
    const b = new EventBuffer({ capacity: 10 });
    assert.equal(b.oldestSeq, null);
    b.append({ seq: 7 }); b.append({ seq: 9 });
    assert.equal(b.oldestSeq, 7);
    assert.equal(b.newestSeq, 9);
});

test('clear resets state', () => {
    const b = new EventBuffer({ capacity: 3 });
    b.append({ seq: 1 });
    b.clear();
    assert.equal(b.size, 0);
    assert.equal(b.append({ seq: 1 }), true);
});
