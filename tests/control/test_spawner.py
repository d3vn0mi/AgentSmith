"""Tests for the Docker SDK wrapper."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_smith.control.spawner import Spawner, SpawnSpec


@pytest.fixture
def fake_docker():
    client = MagicMock()
    container = MagicMock()
    container.id = "cid-abc"
    container.name = "agentsmith-agent-x"
    client.containers.run.return_value = container
    return client


def test_spawn_invokes_docker_run_with_labels(fake_docker):
    sp = Spawner(client=fake_docker, image="agentsmith:latest",
                  network="agentsmith_internal",
                  data_dir_host="/abs/data",
                  config_path_host="/abs/config.yaml",
                  master_key="k", extra_env={"ANTHROPIC_API_KEY": "sk"})
    info = sp.spawn(SpawnSpec(mission_id="m1", agent_id="a1"))
    assert info.container_id == "cid-abc"
    kwargs = fake_docker.containers.run.call_args.kwargs
    assert kwargs["image"] == "agentsmith:latest"
    assert kwargs["command"] == ["python", "-m", "agent_smith", "run-agent"]
    assert kwargs["labels"]["agentsmith.mission_id"] == "m1"
    assert kwargs["labels"]["agentsmith.agent_id"] == "a1"
    assert kwargs["environment"]["MISSION_ID"] == "m1"
    assert kwargs["environment"]["MASTER_KEY"] == "k"
    assert kwargs["environment"]["ANTHROPIC_API_KEY"] == "sk"
    assert kwargs["detach"] is True
    assert kwargs["network"] == "agentsmith_internal"


def test_kill_calls_stop_with_timeout(fake_docker):
    c = MagicMock()
    fake_docker.containers.get.return_value = c
    sp = Spawner(client=fake_docker, image="agentsmith:latest", network="n",
                  data_dir_host="/d", config_path_host="/c.yaml",
                  master_key="k", extra_env={})
    sp.kill("cid-abc", timeout=5)
    fake_docker.containers.get.assert_called_once_with("cid-abc")
    c.stop.assert_called_once_with(timeout=5)


def test_list_by_label(fake_docker):
    c1 = MagicMock(); c1.id = "1"; c1.name = "n1"
    c1.labels = {"agentsmith.mission_id": "m1", "agentsmith.agent_id": "a1"}
    fake_docker.containers.list.return_value = [c1]
    sp = Spawner(client=fake_docker, image="agentsmith:latest", network="n",
                  data_dir_host="/d", config_path_host="/c.yaml",
                  master_key="k", extra_env={})
    listed = sp.list_by_label()
    fake_docker.containers.list.assert_called_once_with(
        all=False, filters={"label": "agentsmith.mission_id"})
    assert len(listed) == 1
    assert listed[0].mission_id == "m1"
    assert listed[0].agent_id == "a1"
