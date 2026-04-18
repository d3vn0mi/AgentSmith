"""Docker SDK wrapper for spawning and managing agent containers."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpawnSpec:
    mission_id: str
    agent_id: str


@dataclass(frozen=True)
class SpawnedInfo:
    container_id: str
    container_name: str


@dataclass(frozen=True)
class LiveAgent:
    container_id: str
    container_name: str
    mission_id: str
    agent_id: str


class Spawner:
    LABEL_MISSION = "agentsmith.mission_id"
    LABEL_AGENT = "agentsmith.agent_id"

    def __init__(self, *, client, image, network, data_dir_host,
                  config_path_host, master_key, extra_env) -> None:
        self._c = client
        self._image = image
        self._network = network
        self._data_dir_host = data_dir_host
        self._config_path_host = config_path_host
        self._master_key = master_key
        self._extra_env = dict(extra_env)

    def spawn(self, spec: SpawnSpec) -> SpawnedInfo:
        name = f"agentsmith-agent-{spec.mission_id[:8]}"
        container = self._c.containers.run(
            image=self._image,
            command=["python", "-m", "agent_smith", "run-agent"],
            name=name,
            environment={
                "MISSION_ID": spec.mission_id,
                "AGENT_ID": spec.agent_id,
                "MASTER_KEY": self._master_key,
                **self._extra_env,
            },
            labels={
                self.LABEL_MISSION: spec.mission_id,
                self.LABEL_AGENT: spec.agent_id,
            },
            volumes={
                self._data_dir_host: {"bind": "/app/data", "mode": "rw"},
                self._config_path_host: {"bind": "/app/config.yaml", "mode": "ro"},
            },
            network=self._network,
            detach=True,
        )
        return SpawnedInfo(container_id=container.id, container_name=container.name)

    def kill(self, container_id: str, *, timeout: int = 10) -> None:
        container = self._c.containers.get(container_id)
        container.stop(timeout=timeout)

    def list_by_label(self) -> list[LiveAgent]:
        cs = self._c.containers.list(
            all=False, filters={"label": self.LABEL_MISSION})
        out = []
        for c in cs:
            labels = c.labels or {}
            out.append(LiveAgent(
                container_id=c.id, container_name=c.name,
                mission_id=labels.get(self.LABEL_MISSION, ""),
                agent_id=labels.get(self.LABEL_AGENT, ""),
            ))
        return out
