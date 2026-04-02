"""Tests for mission state machine."""

from agent_smith.core.mission import HistoryEntry, Mission, Phase


def test_mission_initial_state():
    mission = Mission(target_ip="10.10.10.1")
    assert mission.current_phase == Phase.RECON
    assert mission.iteration == 0
    assert not mission.is_complete()


def test_advance_phase():
    mission = Mission(target_ip="10.10.10.1")
    assert mission.current_phase == Phase.RECON
    mission.advance_phase()
    assert mission.current_phase == Phase.ENUMERATION
    mission.advance_phase()
    assert mission.current_phase == Phase.EXPLOITATION


def test_set_phase():
    mission = Mission(target_ip="10.10.10.1")
    mission.set_phase(Phase.PRIVESC)
    assert mission.current_phase == Phase.PRIVESC


def test_is_complete():
    mission = Mission(target_ip="10.10.10.1")
    assert not mission.is_complete()
    mission.set_phase(Phase.COMPLETE)
    assert mission.is_complete()


def test_over_limit():
    mission = Mission(target_ip="10.10.10.1", max_iterations=5)
    for i in range(5):
        mission.add_history(HistoryEntry(
            iteration=i, phase="recon", thinking="", tool_name="shell",
            tool_args={}, output=""
        ))
    assert mission.is_over_limit()


def test_to_dict():
    mission = Mission(target_ip="10.10.10.1")
    d = mission.to_dict()
    assert d["target_ip"] == "10.10.10.1"
    assert d["current_phase"] == "recon"
    assert d["iteration"] == 0


def test_recent_history():
    mission = Mission(target_ip="10.10.10.1")
    for i in range(30):
        mission.add_history(HistoryEntry(
            iteration=i, phase="recon", thinking="", tool_name="shell",
            tool_args={}, output=f"output_{i}"
        ))
    recent = mission.recent_history(10)
    assert len(recent) == 10
    assert recent[0].output == "output_20"
