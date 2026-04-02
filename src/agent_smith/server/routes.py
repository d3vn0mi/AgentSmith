"""Protected REST API endpoints for mission control."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agent_smith.auth.dependencies import get_current_user, require_role
from agent_smith.auth.models import Role, User

router = APIRouter(prefix="/api", tags=["mission"])

# These are set during app startup by reference to the agent
_get_agent = None  # Callable that returns the AgentSmith instance


def configure_routes(get_agent_fn) -> None:
    global _get_agent
    _get_agent = get_agent_fn


def _agent():
    if _get_agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    agent = _get_agent()
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not running")
    return agent


@router.get("/mission")
async def get_mission(
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get current mission state."""
    agent = _agent()
    return agent.mission.to_dict()


@router.get("/evidence")
async def get_evidence(
    _user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get all collected evidence."""
    agent = _agent()
    return agent.evidence.to_dict()


@router.get("/history")
async def get_history(
    _user: Annotated[User, Depends(get_current_user)],
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get command history."""
    agent = _agent()
    entries = agent.mission.history[-limit:]
    return [
        {
            "iteration": e.iteration,
            "phase": e.phase,
            "thinking": e.thinking,
            "tool_name": e.tool_name,
            "tool_args": e.tool_args,
            "output": e.output,
            "timestamp": e.timestamp,
        }
        for e in entries
    ]


class ControlAction(BaseModel):
    action: str  # "pause", "resume", "inject"
    tool_name: str = ""
    tool_args: dict[str, Any] = {}


@router.post("/control")
async def control(
    action: ControlAction,
    _user: Annotated[User, Depends(require_role(Role.ADMIN, Role.OPERATOR))],
) -> dict[str, Any]:
    """Control the agent: pause, resume, or inject commands."""
    agent = _agent()

    match action.action:
        case "pause":
            agent.mission.paused = True
            return {"status": "paused"}
        case "resume":
            agent.mission.paused = False
            return {"status": "resumed"}
        case "inject":
            if not action.tool_name:
                raise HTTPException(status_code=400, detail="tool_name required for inject")
            output = await agent.inject_command(action.tool_name, action.tool_args)
            return {"status": "executed", "output": output[:2000]}
        case _:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action.action}")


@router.get("/tools")
async def list_tools(
    _user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, str]]:
    """List available tools."""
    agent = _agent()
    return [
        {"name": t.name, "description": t.description}
        for t in agent.tools.list_tools()
    ]
