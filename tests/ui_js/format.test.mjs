import { test } from 'node:test';
import assert from 'node:assert/strict';
import { elapsed, truncate, usd } from '../../src/agent_smith/server/static/js/format.js';

test('elapsed renders mm:ss under an hour', () => {
    assert.equal(elapsed(0),         '00:00');
    assert.equal(elapsed(65_000),    '01:05');
    assert.equal(elapsed(3_599_000), '59:59');
});

test('elapsed renders HH:MM:SS for >= 1 hour', () => {
    assert.equal(elapsed(3_600_000), '01:00:00');
    assert.equal(elapsed(3_725_000), '01:02:05');
});

test('truncate preserves short strings', () => {
    assert.equal(truncate('abc', 5), 'abc');
});

test('truncate adds ellipsis when over limit', () => {
    assert.equal(truncate('abcdefgh', 5), 'abcd\u2026');
});

test('usd formats cents correctly', () => {
    assert.equal(usd(0),     '$0.00');
    assert.equal(usd(0.125), '$0.13');
    assert.equal(usd(1.5),   '$1.50');
});

test('usd passes through null/undefined as em dash', () => {
    assert.equal(usd(null),      '\u2014');
    assert.equal(usd(undefined), '\u2014');
});
