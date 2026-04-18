"""E2E: kali_session_demo driven against a mocked SSH replaying tmux responses.

Asserts the v2 engine runs the playbook to completion without errors and
emits at least one KaliSession fact.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent_smith.controller import MissionController
from agent_smith.event_stream.bus import EventBus
from agent_smith.scenarios.loader import load_playbook


PLAYBOOK = Path("src/agent_smith/playbooks/kali_session_demo.yaml")


class FakeSsh:
    """Returns canned responses keyed by command substring."""

    def __init__(self):
        self.calls: list[str] = []

    async def run_command(self, cmd: str, timeout: int = 60):
        self.calls.append(cmd)

        class R:
            stdout = ""
            stderr = ""
            exit_code = 0
            timed_out = False

        r = R()

        # session_start: command_template contains both "new-session -d" and
        # "has-session" in the same rendered shell script.
        if "new-session -d" in cmd and "has-session" in cmd:
            r.stdout = "OK agentsmith-mshort-runner-xyz\n"
            return r

        # session_exec: script that does send-keys + capture-pane + sentinel.
        if "send-keys" in cmd and "capture-pane" in cmd:
            r.stdout = (
                "echo hello && whoami; echo __END_X\n"
                "hello\n"
                "runner\n"
                "__END_X\n"
            )
            return r

        # session_kill: "tmux kill-session ... echo 'KILLED ..."
        if "kill-session" in cmd and "KILLED" in cmd:
            r.stdout = "KILLED agentsmith-mshort-runner-xyz\n"
            return r

        return r


@pytest.mark.asyncio
async def test_kali_session_demo_runs_end_to_end(tmp_path):
    pb = load_playbook(PLAYBOOK)

    # Pre-substitute the root-task args as the runner does.
    for root in pb.root_tasks:
        for k, v in list(root.args.items()):
            if isinstance(v, str):
                root.args[k] = (
                    v.replace("${MISSION_SHORT_ID}", "mshort")
                     .replace("${MISSION_RANGE_OFFSET}", "0")
                     .replace("${CALLBACK_IP}", "10.10.14.7")
                     .replace("${TARGET}", "10.10.14.7")
                )

    ssh = FakeSsh()
    bus = EventBus()
    controller = MissionController(
        mission_id="m", playbook=pb, ssh=ssh,
        run_dir=tmp_path, bus=bus,
    )
    await controller.run()

    # EvidenceStore.all() returns non-superseded facts (confirmed from store.py).
    facts = list(controller.evidence.all())

    sessions = [f for f in facts if f.type == "KaliSession"]
    assert sessions, (
        f"no KaliSession facts; got types {[f.type for f in facts]}; "
        f"SSH calls made: {len(ssh.calls)}"
    )

    # With the fixed expansion rule, session_start emits live → exec-after-start
    # spawns session_exec → consumes the live session (no fact emitted on
    # successful exec). The store should contain exactly one live KaliSession.
    assert any(f.payload["status"] == "live" for f in sessions)
