# AgentSmith

Autonomous penetration testing agent with a real-time web dashboard.

Given a target IP and SSH access to an attack box, AgentSmith autonomously performs reconnaissance, enumeration, exploitation, and privilege escalation to find `user.txt` and `root.txt` flags. A "Puppet Master" web dashboard provides full transparency into commands, reasoning, and evidence.

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your API keys and admin password
# Edit config.yaml with target IP and attack box details

# 2. Start everything
docker compose up -d

# 3. Create admin user
docker compose exec agentsmith python -m agent_smith seed-admin

# 4. Open dashboard
# https://4g3ntsm1th.d3vn0mi.com (or http://localhost:8080 for local dev)
```

## Architecture

- **Agent Core**: Plan → Execute → Observe → Reason loop following pentest methodology
- **LLM Providers**: Claude, OpenAI, and Ollama (local) with equal support
- **Tool System**: Modular tools (shell, nmap, gobuster, file_ops, exploit)
- **SSH Transport**: AsyncSSH for remote command execution
- **Web Dashboard**: FastAPI + WebSocket real-time UI
- **Auth**: JWT + RBAC (admin, operator, viewer roles)
- **Docker**: Caddy reverse proxy with automatic HTTPS

## Configuration

Edit `config.yaml` to set:
- LLM provider and model
- Target IP address
- Attack box SSH credentials
- Agent parameters (max iterations, timeouts)

## Local Development

```bash
pip install -e ".[dev]"
PYTHONPATH=src python -m agent_smith --config config.yaml
```

## With Local LLM (Ollama)

```bash
docker compose --profile local-llm up -d
# Set provider: "ollama" and model: "llama3.1" in config.yaml
```

## Phase 1 demo (v2 engine skeleton)

The v2 engine runs alongside the existing HTB loop. Phase 1 ships the engine skeleton — DAG graph, typed facts, YAML playbook loader, executor with nmap parser — with no LLM calls.

Run the included skeleton playbook against a host you own:

```bash
PYTHONPATH=src python - <<'PY'
import asyncio, pathlib
from agent_smith.controller import MissionController
from agent_smith.event_stream.bus import EventBus
from agent_smith.scenarios.loader import load_playbook
from agent_smith.transport.ssh import SSHConnection

async def main():
    path = pathlib.Path("src/agent_smith/playbooks/skeleton_portscan.yaml")
    staged = pathlib.Path("/tmp/skeleton_portscan.yaml")
    staged.write_text(path.read_text().replace("${TARGET}", "203.0.113.10"))
    pb = load_playbook(staged)

    ssh = SSHConnection(host="YOUR_ATTACK_BOX_IP", user="root", key_path="~/.ssh/id_rsa")
    await ssh.connect()
    try:
        def builder(spec, args):
            if spec.tool == "nmap":
                return f"nmap -sV -oX - {args['target']}"
            if spec.tool == "curl":
                return f"curl -sS -o /dev/null -w '%{{http_code}}' {args['url']}"
            return spec.tool

        bus = EventBus()
        controller = MissionController(
            mission_id="demo-1",
            playbook=pb,
            ssh=ssh,
            run_dir=pathlib.Path("data/runs/demo-1"),
            bus=bus,
            command_builder=builder,
        )
        await controller.run()
    finally:
        await ssh.disconnect()

asyncio.run(main())
PY
```

Artifacts land under `data/runs/demo-1/`:
- `events.jsonl` — complete event stream
- `tool_runs/*.stdout` / `.stderr` — raw tool outputs

The v2 dashboard panel at the bottom of the existing UI shows the assessment list and graph JSON (created assessments only show up if you POST to `/api/v2/assessments`).

**Phase 1 intentionally omits:** LLM calls, scope guard, approval queue, cost meter, mindmap UI. Those land in Phases 2–4.
