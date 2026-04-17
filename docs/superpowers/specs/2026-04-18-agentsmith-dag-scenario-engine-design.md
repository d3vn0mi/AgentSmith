# AgentSmith v2: DAG-Based Scenario Engine

**Status:** Design approved, pending user review
**Date:** 2026-04-18
**Owner:** d3vn0mi
**Supersedes:** current hardcoded HTB-phase implementation in `src/agent_smith/`

---

## 1. Problem & goals

AgentSmith today is a focused HTB-style autonomous pentester: a hardcoded 5-phase state machine (RECON → ENUM → EXPLOIT → PRIVESC → POST_EXPLOIT), five tool wrappers (shell/nmap/gobuster/file_ops/exploit), an SSH transport to a Kali attack box, a FastAPI+WebSocket "Puppet Master" dashboard, and JWT/RBAC auth. It works for single-box flag hunting; it does not generalize.

We want to evolve it into a general-purpose autonomous pentesting and red-teaming platform with the following guarantees:

- **Any tool on any VM.** Drop curated wrappers in favor of a generic shell executor over SSH. Works against Kali, Parrot, or any Linux box that has the tools installed.
- **Doesn't break the bank.** A simple workflow should cost cents, not dollars. Aggressive prompt caching, rolling summaries, scoped context, small-model routing for cheap decisions.
- **Structured outputs.** Typed facts with schemas and provenance. LLM responses validated against schemas. Reports rendered from typed data, not dumped from free text.
- **Per-step visibility.** Every decision, command, result, fact, and dollar traceable in the dashboard.
- **Multi-scenario.** Same engine runs scoped external pentest (first target), HTB, EASM, and red team as distinct playbooks. Scenarios do not require core code changes.

Two reference projects informed the design. **Talon** (CarbeneAI) contributes methodology playbooks, service-enum guides, Obsidian engagement notes, and OSCP-style report templates. **hexstrike-ai** (0x4m4) contributes patterns: intelligent decision engine, parameter optimizer, process manager, LRU caching, fault-recovery, multi-domain workflow agents. We absorb patterns and artifacts; we do not depend on either project at runtime.

---

## 2. Chosen architecture: DAG-based mission graph

An assessment is a directed acyclic graph of typed tasks. Tasks do not hardcode successors; they declare typed facts they consume and produce. The graph grows dynamically: every fact written to the evidence store may trigger **expansion rules** that materialize new tasks. A **scheduler** picks ready tasks and dispatches them through a **three-tier decision router**. Results flow back as typed facts, which may trigger further expansions.

This shape replaces the current Phase-enum state machine. It was chosen over two alternatives:

- Evolution (layer scenarios on the existing loop) — rejected: HTB shape leaks through; EASM and red team would require another rewrite.
- Replatform around a linear scenario runtime — rejected: does not natively express EASM parallelism or red-team multi-stage missions.

The DAG is ambitious; MVP ships a "thin DAG" — playbooks that are near-linear in practice — but the engine is DAG-shaped from day one so subsequent scenarios land as YAML, not refactors.

---

## 3. Component map

```
┌───────────────────────────────────────────────────────────────────┐
│  Dashboard (FastAPI + WebSocket)   ← carries over, new panels     │
└──────────────────────┬────────────────────────────────────────────┘
                       │ typed events
┌──────────────────────▼────────────────────────────────────────────┐
│  Event Bus (typed)           │  Cost Meter    │  Approval Queue    │
└──────────────────────┬────────┴────────────────┴────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────────────┐
│  Mission Controller                                                │
│    ├── Scenario (playbook + expansion rules + report template)    │
│    ├── Mission Graph (typed tasks, edges = data deps)             │
│    ├── Scheduler (ready-task picker, concurrency, rate limit)     │
│    └── Evidence Store (typed facts with provenance)               │
└──────────────────────┬────────────────────────────────────────────┘
                       │ task dispatch
┌──────────────────────▼────────────────────────────────────────────┐
│  Three-Tier Decision Router                                        │
│    Tier 0  deterministic playbook binding (no LLM)                 │
│    Tier 1  cheap model (Haiku / Ollama) — parse, classify, rank    │
│    Tier 2  capable model (Sonnet) — novel reasoning, narrative     │
└──────────────────────┬────────────────────────────────────────────┘
                       │ command + args
┌──────────────────────▼────────────────────────────────────────────┐
│  Scope Guard + Risk Classifier (pass / queue-for-approval / block)│
└──────────────────────┬────────────────────────────────────────────┘
                       │ approved commands
┌──────────────────────▼────────────────────────────────────────────┐
│  Executor                                                          │
│    ├── Transport (SSH now, WinRM/local later)                     │
│    ├── Process Manager (stream, timeout, kill, PTY)               │
│    ├── Parsers (nmap, feroxbuster, nuclei, cme, + generic)        │
│    └── LRU result cache (skip redundant scans)                    │
└───────────────────────────────────────────────────────────────────┘
```

### What survives from current AgentSmith

- `server/` (FastAPI app, WebSocket, auth routes, static assets). Adds new panels; plumbing unchanged.
- `auth/` (JWT, RBAC). Add permissions `approve_commands` and `edit_scope`.
- `llm/` (provider abstractions). Extend with per-tier model selection.
- `transport/ssh.py` (AsyncSSH). Wrapped by new Executor; base class unchanged.
- `events.py` (event bus). Becomes typed/schema-validated; pub/sub shape unchanged.
- Docker + Caddy + `.env` deploy surface.

### What gets replaced

- `core/agent.py` → Mission Controller + Scheduler + Router.
- `core/mission.py` (Phase enum state machine) → Mission Graph + typed task states.
- `core/evidence.py` (free-text + hardcoded types) → typed fact store with schemas, provenance, dedup, supersede.
- `tools/*.py` (five wrappers) → Executor with generic shell + pluggable parsers. Existing wrappers salvaged as first-class parsers.

### Entirely new modules

- `scenarios/` — playbook loader, expansion matcher, termination evaluator.
- `router/` — three-tier router with cost accounting, cache, circuit breakers.
- `graph/` — Mission Graph data structure, scheduler, dependency resolver.
- `safety/` — scope guard, target extractor, risk classifier, approval queue.
- `reporter/` — Jinja2 template engine + report artifacts.
- Dashboard panels — mindmap, evidence, approval queue, assessment overview, trend panel.

---

## 4. Scenario engine & mission graph

### 4.1 Scenario bundle

A scenario is a declarative bundle (YAML, with Python hook escape hatches):

```yaml
name: external-pentest
version: 1.0
scope_required: true
allowed_risks: [low, medium]
cost_cap_usd: 5.00

root_tasks:
  - port_scan:
      host_set: "{scope.hosts}"

expansions:
  - on_fact: OpenPort{service: http|https}
    spawn: [web_tech_fingerprint, web_dir_enum, nuclei_scan]

  - on_fact: OpenPort{service: ssh}
    spawn: [ssh_audit]

  - on_fact: WebEndpoint{status: 200, interesting: true}
    spawn: [endpoint_probe]

  - on_fact: Credential
    spawn: [cred_spray_authenticated_services]

  - on_fact_python: hooks.external_pentest.on_web_tech

terminations:
  - scope_exhausted
  - cost_cap_hit
  - mission_time_cap
  - operator_halt

report_template: templates/external-pentest.md.j2
```

### 4.2 Task definition

```yaml
task_type: web_dir_enum
consumes:
  host: Host
  port: OpenPort{service: http|https}
produces: [WebEndpoint, Technology, Credential]
tool: feroxbuster
args_template:
  url: "{port.scheme}://{host.ip}:{port.number}"
  wordlist: /usr/share/wordlists/raft-medium.txt
risk: low
timeout: 600
parser: feroxbuster
cache_key: "feroxbuster:{host.ip}:{port.number}"
```

### 4.3 Engine primitives

1. **Typed fact subscription.** Expansion rules fire on fact *shape*, not string match. The matcher supports equality, alternation (`http|https`), existence, negation, numeric range, regex.
2. **Task states:** `pending → ready → awaiting_approval → running → complete | failed | blocked | skipped`. Scheduler only runs `ready`.
3. **Deduplication by canonical key.** Same fact observed twice → one stored fact, multiple provenance entries. Same task with same `cache_key` → deduped.
4. **Fan-out & fan-in built-in.** One fact triggering N parallel tasks is "rule matches N times." A task depending on multiple fact types is "all consumes must exist before ready."
5. **Python hooks** (`on_fact_python`, `custom_terminator`) for branches too gnarly for declarative matching. Most expansions stay YAML.
6. **Budget-aware scheduling.** Per-host concurrency, global concurrency, per-tool rate limiting (OPSEC), cost-cap pause.
7. **Recurrent expansion.** New matching facts arriving late trigger expansions again. A credential discovered at iteration 47 legitimately spawns new tasks. This is what makes red-team multi-stage work on the same primitive.

### 4.4 Explicit non-goals for v1

- **No graph editing mid-run.** The graph grows by expansion only; no manual "delete this subtree" from the UI. Operator can cancel tasks and halt the mission, that's it.
- **No cross-mission fact learning.** Each assessment has its own evidence store. Client confidentiality, not a limitation. A separate reference knowledge base may come later.

---

## 5. Three-tier decision router

The router is a small arbiter that decides which tier handles each decision. Healthy missions run at Tier 0 ($0/step) most of the time. Tiers 1 and 2 are exceptions.

### 5.1 Tier responsibilities

- **Tier 0 — deterministic (no LLM).** Default path. Expansion rule fired, task materialized, `consumes` facts present, `args_template` resolves. Scheduler dispatches directly. Target: 70–85% of task decisions in steady state.

- **Tier 1 — cheap model** (Haiku 4.5 / gpt-4o-mini / Ollama llama3.1-8b). Structured-JSON only. Three bounded jobs:
  1. Generic output parsing (when no structured parser is registered).
  2. Outcome classification (success / partial / fail / blocked-by-WAF) + a one-paragraph summary for rolling history.
  3. Low-stakes ranking of N ready tasks when the playbook declares `rank_strategy: cheap`.

- **Tier 2 — capable model** (Sonnet 4.6 default; Opus 4.7 available for hard pivots). Four bounded jobs:
  1. **Pivot reasoning** — scheduler idle + mission not terminated + untriaged facts present.
  2. **Exploit selection / payload crafting** — for tasks flagged `requires_tier2`.
  3. **Report narrative** — at mission end, fills the scenario's template.
  4. **Tier 1 fallback** — on low confidence or schema-invalid output.

### 5.2 Routing logic

```
expansion rule fires, args resolve                → Tier 0
task completes, structured parser exists          → Tier 0
task completes, no structured parser              → Tier 1 (parse+classify)
N ready tasks, playbook says rank                 → Tier 1 (rank)
scheduler idle + mission not terminated + facts   → Tier 2 (pivot)
task flagged requires_tier2                       → Tier 2
Tier 1 low-confidence or schema-invalid           → Tier 2 (fallback)
Tier 2 proposes high-risk action                  → scope guard → approval queue
```

### 5.3 Cost discipline mechanics

1. **Anthropic prompt caching.** System prompt + scenario playbook + scope manifest + tool catalog marked `cache_control`. Dynamic suffix = recent evidence delta + specific ask. Typical 5–10× reduction on Tier 2 calls.
2. **Rolling summary.** Background Tier 1 job rewrites mission summary every K task completions. Tier 2 receives the summary, never the raw event log.
3. **Scoped context per call.** Router never hands a tier the entire evidence store. Parsing gets `consumes` + command + truncated output. Pivot gets the summary + untriaged fact types. Ranking gets candidate task signatures.
4. **Structured outputs only.** Every tier call uses tool-use or JSON mode with a schema. No free-form prose except the report narrative.
5. **LRU result cache on tool execution.** Same tool + same args + same target within a mission → reuse. Dedupes redundant nmaps.
6. **Per-tier circuit breakers.** Default Tier 2 soft cap: 20 calls/mission. Hard cap = `cost_cap_usd` from the scenario.
7. **Output token budgets.** Tier 1 max ~256; Tier 2 pivot ~1024; report narrative unbounded (end of mission only).

### 5.4 Tier call telemetry

Every router invocation emits a structured event:

```json
{
  "event": "tier_call",
  "task_id": "web_dir_enum#7",
  "tier": 1,
  "model": "claude-haiku-4-5",
  "purpose": "parse_tool_output",
  "input_tokens": 432,
  "cached_tokens": 2100,
  "output_tokens": 87,
  "cost_usd": 0.00034,
  "duration_ms": 512,
  "confidence": 0.92,
  "schema_validated": true
}
```

Cost meter aggregates these live.

### 5.5 Realistic cost targets (aspirational until measured)

- Scoped pentest, 3 hosts, ~8 services, 2-hour mission: **$0.30–$1.50 per run**.
- HTB single-box: **under $0.20 per run**.
- Dominant costs: report narrative + 5–10 Tier 2 pivots.

---

## 6. Evidence & typed facts

### 6.1 Fact shape

```python
@dataclass
class Fact:
    id: str                          # uuid
    type: str                        # "OpenPort", "WebEndpoint", ...
    payload: dict                    # schema-validated per type
    canonical_key: str               # dedup key
    provenance: list[Provenance]     # append-only
    created_at: float
    last_seen_at: float
    superseded_by: str | None
    confidence: float                # 0.0–1.0

@dataclass
class Provenance:
    task_id: str
    tool_run_id: str
    parser: str                      # or "tier1-generic"
    timestamp: float
    snippet: str                     # output fragment
```

### 6.2 MVP fact types

- **Host** `{ip, hostname?, os?, alive}` — key: `host:{ip}`
- **OpenPort** `{host_ip, number, protocol, service?, version?}` — key: `port:{host_ip}:{protocol}:{number}`
- **Technology** `{host_ip, port?, name, version?, cpe?}` — key: `tech:{host_ip}:{port?}:{name}`
- **WebEndpoint** `{url, status, title?, interesting}` — key: `web:{url}`
- **Vulnerability** `{host_ip, port?, cve?, severity, title, evidence}` — key: `vuln:{host_ip}:{cve|title-slug}`
- **Credential** `{username, secret?, secret_type, service_ref?, verified}` — key: `cred:{service_ref?}:{username}`
- **Session** `{host_ip, user, shell_type, transport, privileges}` — key: `sess:{host_ip}:{user}` *(registered but not emitted by MVP parsers; first use is in post-MVP exploitation scenarios)*
- **Flag** `{type, value, host_ip?}` — key: `flag:{type}:{host_ip?}` *(registered but not emitted by MVP parsers; first use is the HTB playbook)*
- **Finding** `{title, severity, hosts[], evidence_refs[], remediation}` — key: `finding:{title-slug}`
- **ScopeViolation** `{target, tool, reason, blocked}` — key: `scope:{timestamp}`

Additional types per scenario (red team: `InternalHost`, `C2Beacon`, `ADPrincipal`, `KerberosTicket`; EASM: `Asset`, `Certificate`, `Subdomain`) added as scenarios come online. Schema registry is extensible.

### 6.3 Dedup + supersede

Same canonical key → one fact, additional `Provenance` appended, `last_seen_at` and `confidence` updated. Supersede applies when a later observation materially changes the payload (e.g., nmap -sV fills in a previously-unknown version). Old fact marked `superseded_by`; queries return the live one by default.

### 6.4 Expansion matcher predicates

Compiled at scenario-load into predicates against payloads:

- Equality: `service: ssh`
- Alternation: `service: http|https`
- Existence / negation: `version: present`, `version: absent`
- Range: `port: 1-1024`
- Regex: `title: ~/admin/i`

Predicates run on every fact insert. New matches fire expansions. This is also how recurrent expansion works.

### 6.5 Parser contract

```python
class Parser(Protocol):
    tool: str
    def parse(self, run: ToolRun) -> list[Fact]: ...
```

**MVP structured parsers** (9): nmap, feroxbuster, gobuster, nuclei, nikto, crackmapexec, hydra, linpeas, smbmap.

**Generic fallback**: Tier 1 call with command + truncated output + scenario-scoped fact-type catalog, asked to emit a list of typed facts as structured JSON. Schema-validated, dedup-routed identically to structured parsers. Low-confidence results quarantined (see §11, risk 2).

### 6.6 Report flow

Reporter renders the scenario's Jinja2 template against a view over the evidence store. Templates loop by fact type (`{% for v in vulnerabilities | severity('high') %}`), pull snippets from provenance, and call Tier 2 once to write narrative. Formats: Markdown (Obsidian-compatible, with front-matter and wiki-links), JSON (machine-readable), optional PDF via pandoc (post-MVP).

---

## 7. Scope guard, risk classifier, approval queue

Every command passing through the Executor hits one middleware layer containing two independent checks in sequence: **scope** (target allowed?) and **risk** (action allowed right now?).

### 7.1 Scope manifest

```yaml
scope:
  in_scope:
    hosts: [203.0.113.0/24]
    domains: ["*.client.example", "client.example"]
    urls: ["https://api.client.example/*"]
  out_of_scope:
    hosts: [203.0.113.5]
    domains: ["mail.client.example"]
    urls: ["*/admin/destroy"]
  engagement_rules:
    no_scan_before: "2026-04-20T09:00:00Z"
    no_scan_after:  "2026-04-25T17:00:00Z"
    rate_limit_pps: 100
    bruteforce_allowed: false
    exploit_allowed: true
    destructive_allowed: false
```

Out-of-scope always wins over in-scope. Engagement rules (time windows, rate limits, allowed action classes) gate separately.

### 7.2 Scope guard logic

For each command:

1. **Extract targets** — IPs, hostnames, URLs, CIDRs. Parser is tool-aware (`nmap` takes targets positional, `curl` takes a URL, `hydra` takes `target://service`) with a generic regex fallback for unknown tools.
2. **Resolve each target** — CIDR membership for hosts, glob match for domains, prefix+pattern for URLs. DNS resolved once at mission start and cached; ambiguous results block the command (defeats DNS rebinding).
3. **Classify outcome** — `in_scope` / `out_of_scope` / `ambiguous` / `unresolvable`.
4. **Apply posture:**
   - **Default (mode B):** `in_scope` → pass. `ambiguous` → queue for approval. `out_of_scope` / `unresolvable` → block + emit `ScopeViolation` fact + notify.
   - **Strict mode (C) flag:** `in_scope` → pass. Everything else → block. Repeated violations (threshold configurable) → mission halt.

### 7.3 Risk classifier

Independent of scope. Tags each command with a risk class:

- **low** — pure read-only recon (`nmap -sV`, `curl -sI`, `dig`, `whois`, passive nuclei templates).
- **medium** — active enumeration visible to target (`feroxbuster`, `gobuster`, active nuclei, SNMP walks, LDAP).
- **high** — bruteforce, credential spray, exploit, anything writing to target.
- **critical** — destructive classes (DoS tooling, disk/file deletion, service restart, plausible availability impact).

Rules are a lookup table (tool + arg patterns) with Tier 1 fallback for unknown tools. Scenario declares `allowed_risks`; anything higher routes to approval (not block). **Critical always requires explicit per-command approval regardless of pre-auth.**

### 7.4 Approval queue

Dashboard panel. Each queued item shows:

```
Task:         web_dir_enum#12
Command:      feroxbuster -u https://admin.client.example:8443 -w raft-medium.txt
Target:       admin.client.example (203.0.113.42)
Scope:        ambiguous — matches *.client.example but not listed explicitly
Risk:         medium (allowed by scenario)
Reasoning:    Tier 2 — "admin subdomain discovered via cert transparency;
              appears in-scope by pattern but not enumerated explicitly"
Cost so far:  $0.23 / $5.00
[Approve] [Approve + pre-auth *.client.example] [Deny] [Deny + halt mission]
```

Scheduler continues running in-scope, within-risk tasks while items await approval. Nothing stalls globally on one approval. RBAC: `operator` actions, `viewer` reads, `admin` can edit scope + rules mid-mission (audit-logged).

### 7.5 Failure modes handled

- Target unparseable → risk classifier flags `unknown` → queued.
- DNS drift mid-mission → guard re-resolves on cadence, divergence blocks + surfaces.
- Scope edits mid-mission → versioned; running tasks complete against their snapshot; new tasks see new version. All edits audit-logged.

---

## 8. Cost, visibility, structured outputs

Per-step visibility is a design constraint, not polish. The event stream is the contract; all UI is a view over it.

### 8.1 Event stream

Every state-changing action emits one typed event. Core types:

- `mission_started` / `mission_complete` / `mission_halted`
- `scenario_loaded` / `scope_loaded` / `scope_edited`
- `task_created` / `task_ready` / `task_awaiting_approval` / `task_running` / `task_complete` / `task_failed` / `task_skipped`
- `expansion_fired`
- `tier_call`
- `tool_run_started` / `tool_run_output` (streamed) / `tool_run_complete`
- `fact_emitted` / `fact_updated` / `fact_superseded`
- `scope_check` / `approval_requested` / `approval_granted` / `approval_denied`
- `budget_warning` / `budget_cap_hit`
- `report_generated`

All events: schema-versioned JSON, carry `mission_id` + optional `task_id` + `timestamp`. Broadcast over WebSocket live and appended to run log.

### 8.2 Run log persistence

Per-mission under `data/runs/{mission_id}/`:

- `events.jsonl` — append-only event log (source of truth).
- `evidence.jsonl` — facts for quick scan.
- `approvals.jsonl` — approval audit.
- `cost.jsonl` — tier call log for cost meter.
- `tool_runs/{run_id}.{stdout,stderr}` — raw tool output.
- `report.md`, `report.json` — final artifacts.
- `evidence.tar.gz` — forensic bundle.

Rolled-up `data/assessments.index.json` for the overview page — loads without rereading every run.

Replay is trivial: reading `events.jsonl` reconstructs dashboard state exactly.

### 8.3 Cost views

- **Live header**: running total, Tier 2 count, Tier 1 count, cache hit %.
- **Assessment overview**: one row per assessment — scenario, scope, status, duration, total cost, Tier 0/1/2 breakdown, facts, findings. Sortable, filterable.
- **Per-task rollup**: every mindmap node carries its attributed cost (sum of tier_calls for that task). Hover-visible, click for tier-by-tier breakdown.
- **Trend panel** (v1): cost per assessment over time, cost-per-scenario averages, Tier 2 call distribution across assessments. Driven off `assessments.index.json`.

Pricing table versioned in-repo, updated manually when providers change prices. Cached tokens priced at provider cache rate. Meter is invoice-exact, not approximate.

### 8.4 Budget mechanisms

- **Soft warning** at 70% of `cost_cap_usd` — banner, no pause.
- **Hard cap** at 100% — scheduler pauses, operator prompt: continue / extend cap / halt.
- **Per-tier circuit breaker** (Tier 2 soft cap, default 20 calls/mission) — separate trip from dollar cap.

### 8.5 Dashboard panels (v2 vs current)

1. **Mindmap panel (new).**
   - Root = assessment (scenario, scope, status).
   - First ring = scenario root tasks.
   - Outer rings = expansion-spawned tasks, radiating by causal depth.
   - Edges: two styles (toggleable) — "spawned by" (expansion provenance) and "data dependency" (consumes/produces).
   - Layout: radial tree by default (mindmap aesthetic), toggleable to DAG force-layout.
   - Coloring: task state. Cost intensity optional heatmap overlay.
   - Live animation as expansions fire.

2. **Evidence panel (new).** Filterable table by fact type, severity, host. Rows expand to provenance + snippet + back-links to observing tasks.

3. **Approval queue panel (new).** See §7.4.

4. **Command stream panel (refit).** Live stdout/stderr, ANSI handling, resumable scroll, per-task filtering.

5. **Assessment overview (new).** Cost + outcome table across all assessments.

6. **Trend panel (new, minimal).** Cost trends, scenario averages, Tier 2 distribution.

Header morphs from (phase, iterations, elapsed) to (scenario, active tasks, ready queue, approvals pending, cost).

### 8.6 Hover vs click detail model

**Hover tooltip** (~200 ms):
```
Task:       web_dir_enum#12
Triggered:  expansion rule "http/https → dir enum" (from OpenPort#7)
Command:    feroxbuster -u https://203.0.113.42:8443 -w raft-medium.txt
State:      complete (42.3 s, exit 0)
Cost:       $0.003  (Tier 1 × 1 parse call)
Output:     last 6 lines [truncated preview]
Facts:      3 × WebEndpoint, 1 × Technology
Artifacts:  stdout.log (14 KB), stderr.log (0 B)
```

**Click side-drawer** (full detail), six tabs:

1. **Trigger** — expansion rule YAML, triggering fact(s) with provenance back-link, scenario reference.
2. **Execution** — full command, resolved args, env, transport, scope-check result, risk classification, approvals.
3. **Output** — full stdout + stderr, syntax-highlighted, searchable, resumable stream while running.
4. **Facts emitted** — list with payloads and provenance snippets.
5. **Artifacts** — every file related to this task (stdout.log, stderr.log, nuclei JSON, nmap XML, etc.), downloadable individually or bundled. Extensible — future parsers register files here.
6. **Cost** — every `tier_call` tied to this task, tier-by-tier, purpose, model, tokens, cost.

### 8.7 Structured output artifacts

Mission end produces under `data/runs/{mission_id}/`:

- `report.md` — scenario template filled, Tier 2 narrative. Obsidian-compatible front-matter + wiki-links.
- `report.json` — machine-readable: findings, hosts, services, vulns, credentials (redacted by default), attack paths.
- `evidence.tar.gz` — raw tool outputs + events + approvals.

### 8.8 Traceability guarantees

- Every command ever run is findable in under three clicks from the mindmap.
- Every cost dollar is attributable to a specific tier call, task, and purpose.
- Every finding in the report links to: the `Vulnerability` fact → observing tasks → raw tool output (with line highlight) → the reasoning that selected the task → the cost to discover it.

"Why is this in the report? How much did it cost?" — both answerable in under 30 seconds from the report view.

---

## 9. Terminology

- **Mission** — code-level data model (compatibility with existing `core/mission.py`).
- **Assessment** — operator-facing term in the dashboard.

These refer to the same entity. The dashboard says "Assessment"; the code says "Mission." A rename pass for the code-level term is optional and not blocking.

---

## 10. MVP scope & build order

### 10.1 Shipped in v1

1. Scenario engine: YAML playbooks + Python hook support.
2. `external_pentest.yaml` playbook — port scan → service fingerprint → web dir enum → nuclei → web tech → endpoint probe → credential discovery. No exploitation, no privesc (deliberately stops at "found the vulnerabilities").
3. Three-tier router with Haiku (Tier 1) + Sonnet (Tier 2) + Anthropic prompt caching.
4. Executor with 9 structured parsers (nmap, feroxbuster, gobuster, nuclei, nikto, crackmapexec, hydra, linpeas, smbmap) + generic Tier 1 fallback + LRU cache.
5. Scope guard mode B default; strict mode (C) flag wired.
6. Risk classifier + scenario `allowed_risks` + approval queue.
7. Typed evidence store with 10 MVP fact types, canonical keys, supersede, JSONL persistence.
8. Dashboard panels: mindmap, evidence, approval queue, assessment overview, cost meter, trend panel.
9. Report generation: Markdown + JSON + evidence tarball.
10. Cost discipline: soft warning at 70%, hard cap at 100%, Tier 2 circuit breaker.

### 10.2 Explicitly out of MVP

- HTB, EASM, red-team playbooks (each is its own spec post-MVP).
- Exploitation and privesc tasks in the pentest playbook.
- Non-SSH transports (WinRM, local, Docker exec).
- Cross-mission fact knowledge base.
- Manual graph editing in UI (cancel-task + halt only).
- PDF report export (client-side pandoc acceptable).
- Non-Anthropic prompt caching (OpenAI/Ollama don't get the 5–10× multiplier; documented).

### 10.3 Build order (5 phases, roughly 1 week each on full-time effort)

Each phase ends with a demoable artifact.

- **Phase 1 — Skeleton.** Typed event bus, Mission Graph, typed evidence store (3 types: Host, OpenPort, WebEndpoint), Executor with nmap parser + generic shell path, playbook loader. Root task dispatches; expansions fire. Demo: YAML playbook runs nmap against scope, emits `OpenPort`, mindmap renders.

- **Phase 2 — Router + cost discipline.** Three-tier router, prompt caching, cost meter, scope guard + risk classifier + approval queue (backend). 5 more parsers. Demo: nmap run costs $0.00 because everything was Tier 0.

- **Phase 3 — Scoped pentest playbook complete.** All 9 parsers. Full `external_pentest.yaml`. Recurrent expansion validated with a credential-reuse scenario. Tier 2 pivot reasoning integrated. Demo: complete assessment against a deliberately vulnerable lab target, report written.

- **Phase 4 — Dashboard v2.** Mindmap, evidence panel with filters, approval queue UI, assessment overview, cost meter, trend panel, hover+click model. Traceability contract met. Demo: operator runs assessment end-to-end through UI only.

- **Phase 5 — Hardening.** Replay, audit log export, strict mode wired, mission-halt UX, failure-recovery polish, docker compose deploy validated with Caddy + HTTPS. Smoke tests against three target types. Demo: ship.

---

## 11. Risks & mitigations

1. **Parser maintenance tax.** Tool output formats drift (nuclei JSON has changed mid-year before). *Mitigation:* parser contract is tiny; parsers live in `parsers/` as independent modules with golden-output fixture tests. Adding a parser is a half-day task.

2. **Tier 1 model quality variance.** Haiku parses nmap fine. Haiku parsing a novel tool's free-form output may hallucinate facts. *Mitigation:* schema-validate every response, confidence threshold, Tier 2 fallback on low confidence, **quarantine low-confidence facts in a separate evidence bucket that expansions don't fire on until operator confirms**.

3. **DAG harder to debug than state machine.** "Why didn't task X run?" needs clear unmet-dependency exposure. *Mitigation:* evidence panel shows which facts each pending task is waiting for; expansion rules log every evaluation to a debug stream.

4. **Approval queue fatigue.** Over-aggressive risk classifier → operators drown and disable the gate. *Mitigation:* aggressive pre-auth options ("approve all medium-risk for this assessment") + per-assessment approval rate reporting for tuning.

5. **MVP is near-linear despite DAG design.** Risk we build fan-out primitives and never exercise them. *Mitigation:* Phase 3's credential-reuse scenario deliberately exercises recurrent expansion. HTB/EASM specs should stress-test fan-out before they ship.

---

## 12. Open decisions deferred to the implementation plan

- Exact schema library (pydantic v2 vs dataclasses + jsonschema). Lean toward pydantic v2 for validator ergonomics.
- Mindmap frontend library (d3-hierarchy vs cytoscape.js vs reactflow). Evaluate in Phase 4.
- Report template engine (Jinja2 is the default; no strong alternative).
- Session/asset naming conventions in Obsidian wiki-links.
- How the scope manifest is uploaded/edited (file drop vs form). Form UX in Phase 4.

None of these are architectural; all can be decided in the implementation plan without redesign.
