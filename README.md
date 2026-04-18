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

## Table of contents

- [What makes AgentSmith different](#what-makes-agentsmith-different)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Running missions](#running-missions)
- [Operational notes](#operational-notes)
- [Development](#development)
- [Project layout](#project-layout)
- [Roadmap](#roadmap)
- [Responsible use](#responsible-use)
- [Acknowledgments](#acknowledgments)
- [License](#license)

---

## What makes AgentSmith different

- **Any tool, any VM.** The executor runs any binary available on your attack box over SSH — no curated wrapper list to maintain. Structured parsers handle the tools whose output the agent reasons about heavily (nmap today; feroxbuster, gobuster, nuclei, nikto, crackmapexec, hydra, linpeas, smbmap coming next).
- **Multi-mission control plane.** Run multiple missions concurrently — each in its own isolated container, each against a different target or Kali profile. The control plane reconciles live containers on restart; no mission state is lost during a redeploy.
- **Three-tier token economics.** Every decision routes through the cheapest tier that can handle it: a deterministic playbook step costs $0; a cheap model (Haiku-class) handles parsing and classification; a capable model (Sonnet-class) is reserved for novel reasoning and report narrative. Target: scoped external pentests under $1.50/run, HTB boxes under $0.20/run.
- **Typed evidence.** Facts like `Host`, `OpenPort`, `WebEndpoint` carry canonical keys, provenance, and confidence. The store dedupes and supersedes automatically. Reports are rendered from typed data, not free-text dumps.
- **Full traceability.** Every state-changing action emits a schema-versioned event. Runs replay from `events.jsonl`. Every finding in the final report links back to the task that observed it and the raw tool output that proved it.
- **Multi-scenario.** The engine runs scoped external pentest, HTB, EASM, and red team as distinct YAML playbooks — no core code changes per scenario.

---

## Architecture

AgentSmith uses a **one image, two entrypoints** model:

```
  docker compose up -d --build
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  agentsmith-control  (python -m agent_smith control-plane)   │
│                                                              │
│  FastAPI server — owns SQLite registry, mounts docker.sock   │
│  ├── /api/profiles    — Kali SSH credential profiles         │
│  ├── /api/missions    — CRUD + WebSocket event stream        │
│  ├── /api/playbooks   — available YAML scenarios             │
│  └── Spawner + Reconciler  — manages agent containers        │
└──────────────────┬───────────────────────────────────────────┘
                   │  docker run  (one per mission)
       ┌───────────┴───────────┐
       ▼                       ▼
┌─────────────────┐   ┌─────────────────────────────┐
│ agentsmith-     │   │ agentsmith-agent-<short-id>  │
│ agent-abc12     │   │   (python -m agent_smith      │
│                 │   │    run-agent)                 │
│  Mission loop   │   │                              │
│  Event writer   │   │  Labels:                     │
│  SSH executor   │   │  agentsmith.mission_id=<id>  │
└─────────────────┘   │  agentsmith.agent_id=<id>   │
                       └─────────────────────────────┘
```

**Key design points:**

- **One image (`agentsmith`), two entrypoints:** `python -m agent_smith control-plane` starts the FastAPI control server; `python -m agent_smith run-agent` starts a mission execution worker. The control plane spawns agent containers dynamically via the Docker socket.
- **Container labeling:** every agent container carries labels `agentsmith.mission_id=<id>` and `agentsmith.agent_id=<id>`. The control plane uses these labels to reconcile live containers on startup — if the control plane restarts mid-mission, it discovers and re-attaches to running agents.
- **Shared `./data` volume:** both the control container and all agent containers mount `./data`. This holds:
  - `data/registry.db` — SQLite database (missions, profiles, users)
  - `data/missions/<mission_id>/events.jsonl` — append-only event log
  - `data/missions/<mission_id>/history.jsonl` — LLM conversation history
  - `data/missions/<mission_id>/evidence.json` — typed evidence store snapshot
  - `data/users.json` — admin/operator user accounts

**Stack:** Python 3.12, FastAPI, Pydantic v2, AsyncSSH, Anthropic / OpenAI / Ollama SDKs, Docker + Caddy (HTTPS), JWT + RBAC auth, SQLite.

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/d3vn0mi/AgentSmith.git
cd AgentSmith

# 2. Configure environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY, JWT_SECRET, MASTER_KEY (or let it auto-generate),
# and ADMIN_PASSWORD for the seed step below.

# 3. Build and start the control plane
docker compose up -d --build

# 4. Seed the admin account
docker exec -e ADMIN_PASSWORD=your_strong_password agentsmith-control \
    python -m agent_smith seed-admin

# 5. Open the dashboard
# https://4g3ntsm1th.d3vn0mi.com  (or http://localhost:8080 for local dev)
```

### First mission walkthrough

1. **Log in** with the admin credentials you just seeded.
2. Open the **Profiles** page → **New profile** — enter your Kali attack box hostname, SSH user, and private key. This credential is stored encrypted using `MASTER_KEY`.
3. Go to **Missions** → **New mission** — pick a playbook, select your Kali profile, enter the target IP. Submit.
4. The control plane spawns an `agentsmith-agent-<short-id>` container. Watch the **Live** tab stream events in real time.

### With a local LLM (Ollama)

```bash
docker compose --profile local-llm up -d
# Set provider: "ollama" and model: "llama3.1" in config.yaml
```

---

## Configuration

`config.yaml` controls global LLM provider settings and server configuration. **Target IP and attack-box credentials are now per-mission** — set them in the **Profiles** and **New mission** UI, not here.

```yaml
llm:
  provider: "claude"                    # claude | openai | ollama
  model:    "claude-sonnet-4-20250514"
  api_key:  "${ANTHROPIC_API_KEY}"

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
  phase_timeout:   1800
```

---

## Running missions

All mission management is through the dashboard UI or the REST API.

### Via the dashboard

1. **Profiles** → create a Kali profile (SSH host, user, key).
2. **Missions** → **New mission** → select playbook + profile + target IP → Submit.
3. Watch the **Live** tab. Switch to **Graph**, **Evidence**, or **History** tabs at any time.
4. Click **Stop** to terminate a running mission gracefully.

### Via the REST API

```bash
# Create a mission
curl -s -X POST https://localhost/api/missions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"playbook": "skeleton_portscan", "profile_id": "<id>", "target": "10.10.11.5"}'

# List missions
curl -s https://localhost/api/missions -H "Authorization: Bearer $TOKEN"

# Stream events (WebSocket)
# ws://localhost/api/missions/<id>/stream?since=0
```

---

## Operational notes

### Stopping a runaway mission

Use the **Stop** button in the dashboard, or from the host shell:

```bash
# Kill by mission ID (safe — leaves the control plane and other missions running)
docker kill $(docker ps --filter label=agentsmith.mission_id=<mission_id> -q)
```

### `MASTER_KEY` warning

`MASTER_KEY` is used to encrypt Kali SSH credentials stored in the registry. On first run, if not set in `.env`, it is auto-generated and written back. **Back it up.** Losing `MASTER_KEY` makes all stored Kali credentials unrecoverable — you would need to re-enter every profile.

### Where data lives

| Path | Contents |
|---|---|
| `./data/registry.db` | SQLite — missions, profiles, users |
| `./data/missions/<id>/events.jsonl` | Append-only event log (replayable) |
| `./data/missions/<id>/history.jsonl` | LLM conversation history per mission |
| `./data/missions/<id>/evidence.json` | Typed evidence snapshot |
| `./data/users.json` | Admin/operator accounts |

### Restart semantics

Restarting the control plane is safe:

```bash
docker compose restart agentsmith-control
```

On startup the control plane queries Docker for containers with `agentsmith.mission_id` labels, reconciles their state against `registry.db`, and re-attaches to any missions that are still running. Browser WebSocket connections reconnect automatically and replay missed events via `?since=<seq>`.

Running agent containers are **not** affected by a control plane restart.

---

## Development

```bash
# Local install with dev deps
pip install -e ".[dev]"

# Run tests
pytest -q

# Start the control plane locally (hot-reload)
PYTHONPATH=src uvicorn agent_smith.server.app:create_app --factory --reload --port 8080
```

**TDD throughout.** Every module has unit tests; the controller has integration tests; an end-to-end test exercises the full mission lifecycle (gated behind an environment flag).

---

## Project layout

```
src/agent_smith/
├── auth/                      # JWT + RBAC (admin, operator, viewer)
├── control/                   # Control-plane internals
│   ├── registry.py           # SQLite mission + profile registry
│   ├── spawner.py            # Docker container lifecycle manager
│   ├── recovery.py           # Startup reconciliation against live containers
│   ├── report.py             # Markdown mission report generator
│   └── crypto.py             # MASTER_KEY encryption for stored credentials
├── agent_runner/              # Agent-container entrypoint
│   ├── runner.py             # Mission execution loop
│   └── event_writer.py       # JSONL event persistence
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

| Phase | Status | Scope |
|---|---|---|
| **Phase 1** | Shipped | DAG engine skeleton: event stream, evidence, mission graph, YAML playbooks, executor, nmap parser, `/api/v2` routes. |
| **Phase 2 (control plane)** | Shipped | Multi-agent control plane: SQLite registry, dynamic container spawning, Docker label reconciliation, profiles, real-time WebSocket dashboard, multi-mission UI. |
| **Phase 3** | Next | Three-tier decision router, prompt caching, cost meter, scope guard + risk classifier + approval queue, 5 more structured parsers. |
| **Phase 4** | Planned | First complete scoped-pentest playbook; Tier 2 pivot reasoning; recurrent expansion end-to-end; full 9-parser MVP set. |
| **Phase 5** | Planned | Hardening: strict-mode scope enforcement, mission-halt UX, failure-recovery polish, replay + audit export, smoke tests against three target classes. |
| **Beyond** | Sketched | HTB playbook, EASM playbook, red-team playbook, optional MCP-client seat for hexstrike-ai interop, WinRM transport. |

---

## Responsible use

AgentSmith is a **dual-use security tool**. It exists to help defenders and authorized testers validate their systems, learn tradecraft, and solve CTFs.

**Only use it against systems you own or for which you have explicit, written authorization to test.** Running reconnaissance, exploitation, or privilege-escalation tooling against systems without permission is illegal in most jurisdictions and ethically indefensible regardless of jurisdiction.

The scope guard and approval queue arriving in Phase 3 are designed to make scoped engagements safer by default. They are not a substitute for a signed statement of work, rules of engagement, and operator judgment.

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
