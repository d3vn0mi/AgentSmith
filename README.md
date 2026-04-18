# AgentSmith

**Autonomous penetration testing agent with a real-time web dashboard.**

```
    _                    _   ____           _ _   _
   / \   __ _  ___ _ __ | |_/ ___| _ __ ___ (_) |_| |__
  / _ \ / _` |/ _ \ '_ \| __\___ \| '_ ` _ \| | __| '_ \
 / ___ \ (_| |  __/ | | | |_ ___) | | | | | | | |_| | | |
/_/   \_\__, |\___|_| |_|\__|____/|_| |_| |_|_|\__|_| |_|
        |___/
```

> Built and maintained by [**d3vn0mi**](https://github.com/d3vn0mi).

AgentSmith drives reconnaissance, enumeration, exploitation, and privilege escalation over SSH against a target you control, while streaming every command, every decision, and every piece of evidence to a "Puppet Master" dashboard for full transparency.

---

## Status

| Component | State | Notes |
|---|---|---|
| **v1 HTB loop** | Stable | Original 5-phase state machine (Recon → Enum → Exploit → PrivEsc → Post). Still works; captures `user.txt` / `root.txt` on CTF-style boxes. |
| **v2 engine skeleton** | Phase 1 shipped | DAG-based scenario engine: typed events, evidence store with dedup + supersede, YAML playbook loader, expansion engine, executor with nmap parser, mission controller, `/api/v2/assessments` routes. 117/117 tests green. |
| **v2 decision router** | Phase 2 (next) | Three-tier router (deterministic → cheap model → capable model), prompt caching, cost meter, scope guard, approval queue. |

See the [Roadmap](#roadmap) for the full multi-phase plan.

---

## Table of contents

- [What makes AgentSmith different](#what-makes-agentsmith-different)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Running an assessment](#running-an-assessment)
- [Development](#development)
- [Project layout](#project-layout)
- [Roadmap](#roadmap)
- [Responsible use](#responsible-use)
- [Acknowledgments](#acknowledgments)
- [License](#license)

---

## What makes AgentSmith different

- **Any tool, any VM.** The v2 executor runs any binary available on your attack box over SSH — no curated wrapper list to maintain. Structured parsers handle the tools whose output the agent reasons about heavily (nmap today; feroxbuster, gobuster, nuclei, nikto, crackmapexec, hydra, linpeas, smbmap coming in Phase 2–3).
- **Three-tier token economics.** Every decision routes through the cheapest tier that can handle it: a deterministic playbook step costs $0; a cheap model (Haiku-class) handles parsing and classification; a capable model (Sonnet-class) is reserved for novel reasoning and report narrative. Target: scoped external pentests under $1.50/run, HTB boxes under $0.20/run.
- **Typed evidence.** Facts like `Host`, `OpenPort`, `WebEndpoint` carry canonical keys, provenance, and confidence. The store dedupes and supersedes automatically. Reports are rendered from typed data, not free-text dumps.
- **Full traceability.** Every state-changing action emits a schema-versioned event. Runs replay from `events.jsonl`. Every finding in the final report links back to the task that observed it and the raw tool output that proved it.
- **Multi-scenario.** The engine runs scoped external pentest (first target), HTB, EASM, and red team as distinct YAML playbooks — no core code changes per scenario.

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│  Dashboard (FastAPI + WebSocket) — "Puppet Master" + v2 panel      │
└──────────────────────┬─────────────────────────────────────────────┘
                       │ typed events
┌──────────────────────▼─────────────────────────────────────────────┐
│  Event Bus (typed)           │  Cost Meter     │  Approval Queue    │
└──────────────────────┬───────┴─────────────────┴─────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────────────┐
│  Mission Controller                                                 │
│    ├── Scenario playbook (YAML + expansion rules)                  │
│    ├── Mission Graph (typed tasks, edges = data deps)              │
│    ├── Scheduler (concurrency + rate limit)                        │
│    └── Evidence Store (typed facts with provenance)                │
└──────────────────────┬─────────────────────────────────────────────┘
                       │ task dispatch
┌──────────────────────▼─────────────────────────────────────────────┐
│  Three-Tier Decision Router  (Phase 2)                              │
│    Tier 0  deterministic playbook binding — no LLM                 │
│    Tier 1  cheap model — parse, classify, rank                     │
│    Tier 2  capable model — novel reasoning, narrative              │
└──────────────────────┬─────────────────────────────────────────────┘
                       │ command + args
┌──────────────────────▼─────────────────────────────────────────────┐
│  Scope Guard + Risk Classifier   (Phase 2)                          │
└──────────────────────┬─────────────────────────────────────────────┘
                       │ approved commands
┌──────────────────────▼─────────────────────────────────────────────┐
│  Executor — SSH transport, process manager, parsers, LRU cache      │
└────────────────────────────────────────────────────────────────────┘
```

**Stack.** Python 3.11+, FastAPI, Pydantic v2, AsyncSSH, Anthropic / OpenAI / Ollama SDKs, Docker + Caddy (HTTPS), JWT + RBAC auth.

---

## Quick start

```bash
# 1. Clone and configure
git clone https://github.com/d3vn0mi/AgentSmith.git
cd AgentSmith
cp .env.example .env
# Edit .env with your API keys and admin password
# Edit config.yaml with target IP and attack box details

# 2. Start everything
docker compose up -d

# 3. Create admin user
docker compose exec agentsmith python -m agent_smith seed-admin

# 4. Open dashboard
# https://4g3ntsm1th.d3vn0mi.com  (or http://localhost:8080 for local dev)
```

### With a local LLM (Ollama)

```bash
docker compose --profile local-llm up -d
# Set provider: "ollama" and model: "llama3.1" in config.yaml
```

---

## Configuration

`config.yaml` controls everything:

```yaml
llm:
  provider: "claude"                    # claude | openai | ollama
  model:    "claude-sonnet-4-6"
  api_key:  "${ANTHROPIC_API_KEY}"

target:
  ip: ""                                # the box you're assessing

attack_box:                             # where tools execute from
  host: ""
  user: "root"
  key_path: "~/.ssh/id_rsa"

server:
  host: "0.0.0.0"
  port: 8080
  domain: "4g3ntsm1th.d3vn0mi.com"

auth:
  jwt_secret:           "${JWT_SECRET}"
  access_token_expiry:  3600
  refresh_token_expiry: 604800
  users_file:           "data/users.json"

agent:
  max_iterations:  200
  command_timeout: 120
  phase_timeout:   1800                 # per-phase cap for v1 loop
```

---

## Running an assessment

### v1 HTB loop (legacy, stable)

Point it at a single CTF-style box. The agent runs the full 5-phase kill chain autonomously and captures flags:

```bash
PYTHONPATH=src python -m agent_smith --config config.yaml
```

### v2 engine (scoped external pentest — scaffolded, evolving)

The v2 engine runs alongside the v1 loop. Phase 1 ships the DAG skeleton: YAML playbook → port scan → expansion rule fires per open HTTP/HTTPS port → per-port tasks spawn. No LLM calls yet — those land in Phase 2.

Run the included skeleton playbook against a host you own:

```bash
PYTHONPATH=src python - <<'PY'
import asyncio, pathlib
from agent_smith.controller import MissionController
from agent_smith.event_stream.bus import EventBus
from agent_smith.scenarios.loader import load_playbook
from agent_smith.transport.ssh import SSHConnection

async def main():
    src = pathlib.Path("src/agent_smith/playbooks/skeleton_portscan.yaml")
    staged = pathlib.Path("/tmp/skeleton_portscan.yaml")
    staged.write_text(src.read_text().replace("${TARGET}", "203.0.113.10"))
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
- `events.jsonl` — every event, replay-able
- `tool_runs/*.stdout` / `.stderr` — raw tool outputs, indexed by run id

The v2 dashboard panel at the bottom of the existing UI shows the assessment list and graph JSON. Assessments created via `POST /api/v2/assessments` appear in the list; Phase 4 will wire the "run this assessment" button.

---

## Development

```bash
# Local install with dev deps
pip install -e ".[dev]"

# Run tests
PYTHONPATH=src pytest tests/ -v

# Run just the v2 suite
PYTHONPATH=src pytest tests/v2/ -v

# Start the server locally (hot-reload)
PYTHONPATH=src uvicorn agent_smith.server.app:create_app --factory --reload --port 8080
```

**TDD throughout.** Phase 1 was implemented test-first across 27 commits; every module has unit tests, the controller has integration tests, and an end-to-end test exercises the full skeleton.

---

## Project layout

```
src/agent_smith/
├── auth/                      # JWT + RBAC (admin, operator, viewer)
├── core/                      # v1 HTB loop (legacy, stable)
│   ├── agent.py              # Plan → Execute → Observe → Reason loop
│   ├── mission.py            # Phase enum state machine
│   └── evidence.py           # Free-text evidence (legacy)
├── llm/                       # Provider abstractions (Claude / OpenAI / Ollama)
├── tools/                     # v1 tool wrappers (shell, nmap, gobuster, …)
├── transport/                 # AsyncSSH connection + SFTP
├── server/                    # FastAPI + WebSocket dashboard
│
├── event_stream/              # v2: typed Event, EventBus, JSONL persistence
├── evidence/                  # v2: typed Fact store with dedup + supersede
├── graph/                     # v2: Task, MissionGraph, Scheduler
├── scenarios/                 # v2: YAML playbook loader + ExpansionEngine
├── executor/                  # v2: ShellRunner, Executor, parser registry
├── controller.py              # v2: MissionController (end-to-end loop)
└── playbooks/                 # v2: YAML scenario playbooks
```

---

## Roadmap

Built in phases so each ships something usable.

| Phase | Status | Scope |
|---|---|---|
| **Phase 1** | Shipped | DAG engine skeleton: event stream, evidence, mission graph, YAML playbooks, executor, nmap parser, `/api/v2` routes, demo dashboard panel. |
| **Phase 2** | Next | Three-tier decision router, prompt caching, cost meter, scope guard + risk classifier + approval queue (backend), 5 more structured parsers, LRU result cache, generic Tier 1 fallback. |
| **Phase 3** | Planned | First complete scoped-pentest playbook; Tier 2 pivot reasoning; recurrent expansion end-to-end; full 9-parser MVP set. |
| **Phase 4** | Planned | Dashboard v2: mindmap panel, evidence panel with filters, approval queue UI, per-assessment cost rollup, cross-assessment trend view. |
| **Phase 5** | Planned | Hardening: strict-mode scope enforcement, mission-halt UX, failure-recovery polish, replay + audit export, smoke tests against three target classes. |
| **Beyond** | Sketched | HTB playbook, EASM playbook, red-team playbook, optional MCP-client seat for hexstrike-ai interop, WinRM transport. |

---

## Responsible use

AgentSmith is a **dual-use security tool**. It exists to help defenders and authorized testers validate their systems, learn tradecraft, and solve CTFs.

**Only use it against systems you own or for which you have explicit, written authorization to test.** Running reconnaissance, exploitation, or privilege-escalation tooling against systems without permission is illegal in most jurisdictions and ethically indefensible regardless of jurisdiction.

The scope guard and approval queue arriving in Phase 2 are designed to make scoped engagements safer by default. They are not a substitute for a signed statement of work, rules of engagement, and operator judgment.

**If you're not sure whether you have authorization, you don't.**

---

## Acknowledgments

AgentSmith stands on the shoulders of two open-source projects whose patterns shaped the v2 design:

- **[Talon](https://github.com/CarbeneAI/Talon)** by [@CarbeneAI](https://github.com/CarbeneAI) — contributed the methodology DNA: structured multi-phase recon, service-specific enumeration guides, OSCP-style reporting, and Obsidian engagement templates.
- **[hexstrike-ai](https://github.com/0x4m4/hexstrike-ai)** by [@0x4m4](https://github.com/0x4m4) — contributed the pattern DNA: intelligent decision engine, parameter optimizer, process management, LRU caching, failure recovery, and multi-domain workflow agents.

AgentSmith absorbs those patterns and artifacts; it does not depend on either project at runtime.

---

## License

[MIT](./LICENSE) © 2026 [d3vn0mi](https://github.com/d3vn0mi)

---

<p align="center"><sub>Made in the terminal, for the terminal.</sub></p>
