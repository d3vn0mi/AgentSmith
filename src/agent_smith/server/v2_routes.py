"""Phase 1 HTTP surface for the v2 engine.

Creates and lists assessments, exposes the mission graph as JSON. Execution
via HTTP lands in Phase 4; for Phase 1 the integration test drives the
controller directly.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent_smith.graph.mission_graph import MissionGraph


router = APIRouter(prefix="/api/v2", tags=["assessments-v2"])


@dataclass
class _AssessmentRecord:
    mission_id: str
    playbook: str
    target: str
    status: str = "created"
    graph: MissionGraph | None = None


class _Store:
    def __init__(self) -> None:
        self.base_dir: Path = Path("data/runs")
        self.records: dict[str, _AssessmentRecord] = {}

    def reset(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.records = {}


AssessmentStore = _Store()


class CreateAssessmentRequest(BaseModel):
    playbook: str
    target: str


class CreateAssessmentResponse(BaseModel):
    mission_id: str
    status: str
    playbook: str
    target: str


class AssessmentSummary(BaseModel):
    mission_id: str
    status: str
    playbook: str
    target: str


@router.post("/assessments", status_code=201, response_model=CreateAssessmentResponse)
async def create_assessment(body: CreateAssessmentRequest) -> CreateAssessmentResponse:
    mission_id = str(uuid.uuid4())
    AssessmentStore.records[mission_id] = _AssessmentRecord(
        mission_id=mission_id,
        playbook=body.playbook,
        target=body.target,
    )
    return CreateAssessmentResponse(
        mission_id=mission_id, status="created",
        playbook=body.playbook, target=body.target,
    )


@router.get("/assessments", response_model=list[AssessmentSummary])
async def list_assessments() -> list[AssessmentSummary]:
    return [
        AssessmentSummary(
            mission_id=r.mission_id, status=r.status,
            playbook=r.playbook, target=r.target,
        )
        for r in AssessmentStore.records.values()
    ]


@router.get("/assessments/{mission_id}/graph")
async def get_graph(mission_id: str) -> dict[str, Any]:
    record = AssessmentStore.records.get(mission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="assessment not found")
    if record.graph is None:
        return {"mission_id": mission_id, "total": 0, "finished": 0, "tasks": []}
    return record.graph.to_dict()
