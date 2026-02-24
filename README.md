> **Disclaimer:** This entire project was vibe coded using [Claude Code](https://claude.ai/code). No guarantees, no warranty — just vibes and AI.

---

# Homelab Assistant

A private, cloud-first personal assistant for homelab servers (TrueNAS SCALE). Designed to let you query your server through natural language — safely and with full auditability.

> **Stage 1 — Server Monitoring (Read-Only):** The assistant can answer questions about your system but cannot execute any actions.

---

## Architecture

```
Client
  │
  ▼
Gateway (8000)        ← HTTPS entrypoint, API key auth, rate limiting
  │
  ▼
Orchestrator (8001)   ← Assistant core, policy enforcement, audit logging
  │          │
  ▼          ▼
LLM Adapter  Tool Monitoring (8003)
(8002)       └── CPU, memory, disk, container status
```

All services run as containers on an internal Docker network. Only the Gateway is externally exposed.

| Service | Port | Responsibility |
|---|---|---|
| Gateway | 8000 | Auth, rate limiting, HTTPS entrypoint |
| Orchestrator | 8001 | Intent routing, policy enforcement, audit logs |
| LLM Adapter | 8002 | Abstraction over cloud LLM providers (Groq, OpenAI) |
| Tool Monitoring | 8003 | Read-only system and container metrics |

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- A [Groq API key](https://console.groq.com) (free tier) or OpenAI API key

### Setup

```bash
cd homelab-assistant/deploy
cp .env.example .env
# Edit .env and fill in your API_KEY and GROQ_API_KEY
```

### Run

```bash
cd homelab-assistant/deploy
docker-compose up --build
```

### Test

```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "What containers are running?"}'
```

---

## What You Can Ask

```
"Is everything running correctly?"
"What containers are currently running?"
"How much disk space is left?"
"What is the current CPU and memory usage?"
"Did any service crash recently?"
```

## What the Assistant Will Refuse

Any state-changing or destructive operation is explicitly blocked:

- Restarting services or containers
- Filesystem or snapshot changes
- Firewall or network changes
- Shell command execution
- Scheduling or automation

---

## Configuration

| Variable | Service | Description |
|---|---|---|
| `API_KEY` | Gateway | Client authentication key |
| `LLM_PROVIDER` | LLM Adapter | `groq` (default) or `openai` |
| `GROQ_API_KEY` | LLM Adapter | Groq API key |
| `OPENAI_API_KEY` | LLM Adapter | OpenAI API key (if using OpenAI) |
| `RATE_LIMIT_REQUESTS` | Gateway | Max requests per window (default: 60) |
| `RATE_LIMIT_WINDOW` | Gateway | Window duration in seconds (default: 60) |
| `LOG_LEVEL` | All | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |

---

## Project Structure

```
homelab-assistant/
├── apps/
│   ├── gateway/          # Auth, rate limiting
│   ├── orchestrator/     # Core logic, policy enforcement
│   ├── llm_adapter/      # Groq / OpenAI provider abstraction
│   ├── tool_monitoring/  # System metrics and container status
│   └── frontend/         # Web UI (React + TypeScript)
├── packages/
│   ├── homelab_schemas/  # Shared Pydantic models
│   └── homelab_common/   # Shared config and logging
└── deploy/
    ├── docker-compose.yml
    └── .env.example
```

---

## Audit Logging

Every conversation is logged to `/var/log/homelab-assistant/audit.jsonl` (append-only JSONL):

```json
{
  "timestamp": "...",
  "conversation_id": "...",
  "user_message": "...",
  "assistant_response": "...",
  "tool_calls": [...]
}
```

Logs never include credentials or API keys.

---

## Roadmap

- **Stage 1 (current):** Read-only server monitoring
- **Stage 2:** Confirmed write actions (restarts, container management)
- **Stage 3:** Local LLM support
- **Stage 4:** Automation and scheduling

---

## Built with

- [Claude Code](https://claude.ai/code) — AI-assisted development by Anthropic
- [FastAPI](https://fastapi.tiangolo.com/) — Python web framework
- [Groq](https://console.groq.com) — LLM inference
- [Docker](https://www.docker.com/) — Containerization
- [React](https://react.dev/) + [Vite](https://vitejs.dev/) — Frontend
