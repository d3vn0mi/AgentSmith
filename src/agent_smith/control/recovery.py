"""Startup reconciliation: align DB with live agent containers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from agent_smith.control.registry import Registry


TERMINAL_EVENT_TO_STATUS = {
    "mission.completed": "completed",
    "mission.stopped":   "stopped",
}


def _last_event_type(events_path: Path) -> Optional[str]:
    if not events_path.exists():
        return None
    last: Optional[str] = None
    with events_path.open("rb") as fh:
        for raw in fh:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                last = json.loads(line).get("type")
            except json.JSONDecodeError:
                continue
    return last


def reconcile(registry: Registry, spawner, *, data_dir: Path) -> None:
    live_ids = {la.container_id for la in spawner.list_by_label()}
    for a in registry.list_agents(statuses=("pending", "running")):
        if a.container_id and a.container_id in live_ids:
            continue
        registry.close_agent(a.id, status="exited", exit_code=None)
        events = data_dir / "missions" / a.mission_id / "events.jsonl"
        last = _last_event_type(events)
        mission_status = TERMINAL_EVENT_TO_STATUS.get(last, "failed")
        registry.set_mission_status(a.mission_id, mission_status, ended_at=True)
