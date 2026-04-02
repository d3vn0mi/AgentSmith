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
