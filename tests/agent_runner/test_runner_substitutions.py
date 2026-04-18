"""Tests for mission-scope substitutions in _run_v2_engine."""
from __future__ import annotations

import hashlib

from agent_smith.agent_runner.runner import _build_substitutions


def test_substitutions_include_target():
    class _M:
        id = "7be2bc45-3bca-49eb-9663-da6ccaf6fa41"
        target = "10.129.0.1"
    class _P:
        callback_ip = None
    s = _build_substitutions(_M(), _P())
    assert s["${TARGET}"] == "10.129.0.1"


def test_mission_short_id_is_first_8_chars():
    class _M:
        id = "7be2bc45-3bca-49eb-9663-da6ccaf6fa41"
        target = "t"
    class _P:
        callback_ip = None
    assert _build_substitutions(_M(), _P())["${MISSION_SHORT_ID}"] == "7be2bc45"


def test_mission_range_offset_is_stable_across_calls():
    class _M:
        id = "mission-abc"
        target = "t"
    class _P:
        callback_ip = None
    s1 = _build_substitutions(_M(), _P())["${MISSION_RANGE_OFFSET}"]
    s2 = _build_substitutions(_M(), _P())["${MISSION_RANGE_OFFSET}"]
    assert s1 == s2
    expected = int.from_bytes(
        hashlib.sha256(b"mission-abc").digest()[:4], "big") % 80
    assert s1 == str(expected)


def test_callback_ip_falls_back_to_empty():
    class _M:
        id = "m"
        target = "t"
    class _P:
        callback_ip = None
    assert _build_substitutions(_M(), _P())["${CALLBACK_IP}"] == ""


def test_callback_ip_uses_profile_value_when_set():
    class _M:
        id = "m"
        target = "t"
    class _P:
        callback_ip = "10.10.14.7"
    assert _build_substitutions(_M(), _P())["${CALLBACK_IP}"] == "10.10.14.7"
