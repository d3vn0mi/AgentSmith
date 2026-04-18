import { test } from 'node:test';
import assert from 'node:assert/strict';
import { categorize, KINDS } from '../../src/agent_smith/server/static/js/event_types.js';

test('categorize — thinking', () => {
    assert.equal(categorize('thinking').kind, 'thinking');
    assert.equal(categorize('thought').kind, 'thinking');
    assert.equal(categorize('agent.thinking').kind, 'thinking');
});

test('categorize — tool', () => {
    assert.equal(categorize('command_executing').kind, 'tool');
    assert.equal(categorize('command_executed').kind, 'tool');
    assert.equal(categorize('tool.run_started').kind, 'tool');
    assert.equal(categorize('tool_run_output').kind, 'tool');
});

test('categorize — evidence / finding', () => {
    assert.equal(categorize('evidence_updated').kind, 'evidence');
    assert.equal(categorize('evidence.added').kind,   'evidence');
    assert.equal(categorize('fact_emitted').kind,     'evidence');
    assert.equal(categorize('flag_captured').kind,    'finding');
});

test('categorize — phase / mission', () => {
    assert.equal(categorize('phase_changed').kind, 'phase');
    assert.equal(categorize('phase.entered').kind, 'phase');
    assert.equal(categorize('mission.started').kind,  'mission');
    assert.equal(categorize('mission_complete').kind, 'mission');
});

test('categorize — error', () => {
    assert.equal(categorize('error').kind, 'error');
    assert.equal(categorize('tool.failed').kind, 'error');
    assert.equal(categorize('mission.failed').kind, 'error');
});

test('categorize — unknown falls back to other', () => {
    assert.equal(categorize('some_random_event').kind, 'other');
});

test('KINDS exports expected set', () => {
    assert.ok(KINDS.includes('thinking'));
    assert.ok(KINDS.includes('tool'));
    assert.ok(KINDS.includes('evidence'));
    assert.ok(KINDS.includes('finding'));
    assert.ok(KINDS.includes('phase'));
    assert.ok(KINDS.includes('mission'));
    assert.ok(KINDS.includes('error'));
    assert.ok(KINDS.includes('other'));
});
