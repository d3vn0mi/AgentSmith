"""REST + WS for missions."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_smith.control.registry import Registry
from agent_smith.control.spawner import Spawner, SpawnSpec


router = APIRouter(tags=["missions"])

_registry: Optional[Registry] = None
_spawner: Optional[Spawner] = None
_data_dir: Optional[Path] = None
_auth_disabled_for_tests = False


def configure(reg: Registry, spawner: Spawner, *,
               data_dir: Path, auth_disabled_for_tests: bool = False) -> None:
    global _registry, _spawner, _data_dir, _auth_disabled_for_tests
    _registry = reg
    _spawner = spawner
    _data_dir = data_dir
    _auth_disabled_for_tests = auth_disabled_for_tests


class MissionIn(BaseModel):
    name: str
    target: str
    playbook: str
    kali_profile_id: str
    agent_config: Optional[dict] = None


class MissionOut(BaseModel):
    id: str
    name: str
    target: str
    playbook: str
    kali_profile_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None


class MissionDetailOut(MissionOut):
    agents: list


def _to_out(m) -> MissionOut:
    return MissionOut(
        id=m.id, name=m.name, target=m.target, playbook=m.playbook,
        kali_profile_id=m.kali_profile_id, status=m.status,
        created_at=m.created_at, started_at=m.started_at, ended_at=m.ended_at,
    )


@router.get("/api/missions", response_model=list[MissionOut])
async def list_missions():
    assert _registry
    return [_to_out(m) for m in _registry.list_missions()]


@router.post("/api/missions", response_model=MissionOut, status_code=201)
async def create_mission(body: MissionIn):
    assert _registry and _spawner and _data_dir is not None
    if _registry.get_profile(body.kali_profile_id) is None:
        raise HTTPException(400, "unknown kali_profile_id")
    m = _registry.create_mission(
        name=body.name, target=body.target, playbook=body.playbook,
        kali_profile_id=body.kali_profile_id,
        agent_config=body.agent_config or {})
    a = _registry.create_agent(mission_id=m.id)
    (_data_dir / "missions" / m.id).mkdir(parents=True, exist_ok=True)

    info = _spawner.spawn(SpawnSpec(mission_id=m.id, agent_id=a.id))
    _registry.set_agent_running(
        a.id, container_id=info.container_id,
        container_name=info.container_name)
    _registry.set_mission_status(m.id, "running", started_at=True)
    return _to_out(_registry.get_mission(m.id))


@router.get("/api/missions/{mission_id}", response_model=MissionDetailOut)
async def get_mission(mission_id: str):
    assert _registry
    m = _registry.get_mission(mission_id)
    if m is None:
        raise HTTPException(404)
    agents = _registry.list_agents_for_mission(mission_id)
    return MissionDetailOut(**_to_out(m).model_dump(),
                             agents=[a.__dict__ for a in agents])


@router.post("/api/missions/{mission_id}/stop", status_code=204)
async def stop_mission(mission_id: str):
    assert _registry and _spawner
    m = _registry.get_mission(mission_id)
    if m is None:
        raise HTTPException(404)
    if m.status != "running":
        raise HTTPException(400, "mission not running")
    for a in _registry.list_agents_for_mission(mission_id):
        if a.container_id and a.status == "running":
            try:
                _spawner.kill(a.container_id, timeout=10)
            except Exception:
                pass


@router.get("/api/playbooks")
async def list_playbooks():
    pbdir = Path(os.environ.get("PLAYBOOKS_DIR",
                                  "src/agent_smith/playbooks"))
    if not pbdir.is_dir():
        return []
    out = []
    for p in sorted(pbdir.glob("*.yaml")):
        out.append({"filename": p.name, "name": p.stem, "description": ""})
    return out


import json as _json
from typing import Iterator


def _iter_events(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield _json.loads(line)
            except _json.JSONDecodeError:
                continue


@router.get("/api/missions/{mission_id}/events")
async def get_events(
    mission_id: str,
    after: Optional[int] = None,
    before: Optional[int] = None,
    limit: int = 200,
    types: Optional[str] = None,
):
    assert _registry and _data_dir is not None
    if _registry.get_mission(mission_id) is None:
        raise HTTPException(404)
    limit = max(1, min(limit, 1000))
    type_set = {t for t in (types.split(",") if types else []) if t}
    events_path = _data_dir / "missions" / mission_id / "events.jsonl"
    events = list(_iter_events(events_path))
    if type_set:
        events = [e for e in events if e.get("type") in type_set]

    if before is not None:
        slc = [e for e in events if e.get("seq", -1) < before]
        return list(reversed(slc))[:limit]
    start = after if after is not None else -1
    slc = [e for e in events if e.get("seq", -1) > start]
    return slc[:limit]


import asyncio as _asyncio

from fastapi import WebSocket, WebSocketDisconnect


@router.websocket("/ws/missions/{mission_id}")
async def mission_ws(ws: WebSocket, mission_id: str, since: int = -1):
    assert _registry and _data_dir is not None
    if _registry.get_mission(mission_id) is None:
        await ws.close(code=4404)
        return
    await ws.accept()

    events_path = _data_dir / "missions" / mission_id / "events.jsonl"
    for e in _iter_events(events_path):
        if e.get("seq", -1) > since:
            await ws.send_json(e)
            since = e.get("seq", since)
    last_size = events_path.stat().st_size if events_path.exists() else 0

    try:
        while True:
            await _asyncio.sleep(0.25)
            if not events_path.exists():
                continue
            cur = events_path.stat().st_size
            if cur == last_size:
                continue
            for e in _iter_events(events_path):
                seq = e.get("seq", -1)
                if seq > since:
                    since = seq
                    await ws.send_json(e)
            last_size = cur
    except WebSocketDisconnect:
        return


from fastapi.responses import Response

from agent_smith.control import report as _report


@router.get("/api/missions/{mission_id}/report.md")
async def get_report(mission_id: str):
    assert _registry and _data_dir is not None
    if _registry.get_mission(mission_id) is None:
        raise HTTPException(404)
    md = _report.render(_registry, mission_id, data_dir=_data_dir)
    filename = f"mission-{mission_id[:8]}.md"
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
