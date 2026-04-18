"""Markdown mission report renderer."""
from __future__ import annotations

import json
from pathlib import Path

from agent_smith.control.registry import Registry


def render(registry: Registry, mission_id: str, *, data_dir: Path) -> str:
    m = registry.get_mission(mission_id)
    if m is None:
        raise KeyError(mission_id)
    profile = registry.get_profile(m.kali_profile_id)
    profile_name = profile.name if profile else "(deleted)"
    mdir = data_dir / "missions" / mission_id

    evidence = {}
    ep = mdir / "evidence.json"
    if ep.exists():
        try:
            evidence = json.loads(ep.read_text())
        except json.JSONDecodeError:
            evidence = {}

    history = []
    hp = mdir / "history.jsonl"
    if hp.exists():
        for raw in hp.read_text().splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                history.append(json.loads(raw))
            except json.JSONDecodeError:
                continue

    lines: list[str] = []
    lines.append(f"# Mission: {m.name}")
    lines.append("")
    lines.append(f"- **Target:** `{m.target}`")
    lines.append(f"- **Playbook:** `{m.playbook}`")
    lines.append(f"- **Kali profile:** {profile_name}")
    lines.append(f"- **Status:** {m.status}")
    lines.append(f"- **Created:** {m.created_at}")
    lines.append(f"- **Started:** {m.started_at or '-'}")
    lines.append(f"- **Ended:** {m.ended_at or '-'}")
    lines.append("")

    def _section(title, items, fmt):
        lines.append(f"## {title}")
        if not items:
            lines.append("_none_")
        else:
            for it in items:
                lines.append(f"- {fmt(it)}")
        lines.append("")

    _section("Flags", evidence.get("flags", []), lambda x: f"`{x}`")
    _section("Ports", evidence.get("ports", []),
              lambda x: f"`{x.get('port','?')}/{x.get('service','?')}`")
    _section("Credentials", evidence.get("credentials", []),
              lambda x: f"`{x}`")
    _section("Vulnerabilities", evidence.get("vulnerabilities", []),
              lambda x: f"`{x}`")
    _section("Files", evidence.get("files", []), lambda x: f"`{x}`")

    lines.append("## Command history")
    if not history:
        lines.append("_none_")
    else:
        for entry in history:
            cmd = entry.get("command", "")
            ec = entry.get("exit_code", "?")
            lines.append(f"- `$ {cmd}` → exit {ec}")
    lines.append("")

    return "\n".join(lines)
