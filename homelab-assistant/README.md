# Homelab Assistant

A private, cloud-first personal assistant for homelab servers (TrueNAS SCALE) — query your system health and container status using natural language.

> **Stage 1: Read-Only Monitoring.** The assistant can only retrieve system information. All state-changing operations (restarts, filesystem changes, etc.) are explicitly refused.

---

## Architecture

```
Gateway (8000) → Orchestrator (8001) → LLM Adapter (8002)
                       ↓
                Tool Monitoring (8003)

Frontend (3000) → Gateway (8000)
```

| Service | Port | Responsibility |
|---------|------|----------------|
| **Gateway** | 8000 | HTTPS entrypoint, API key authentication, rate limiting. The only externally exposed service. |
| **Orchestrator** | 8001 | Assistant core. Validates tool calls, enforces read-only policy, writes audit logs. |
| **LLM Adapter** | 8002 | Abstracts cloud LLM providers (Groq, OpenAI) behind a common interface. |
| **Tool Monitoring** | 8003 | Exposes read-only system metrics (CPU, memory, disk) and Docker container status. |
| **Frontend** | 3000 | Web chat UI (served via nginx). |

Services communicate over an internal Docker bridge network. Shared Pydantic models and utilities live in `packages/`.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- A **Groq** API key (free tier at [console.groq.com](https://console.groq.com)) **or** an **OpenAI** API key

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/JDebon/homelab-assistant.git
cd homelab-assistant/homelab-assistant

# 2. Configure environment
cd deploy
cp .env.example .env
# Edit .env and set API_KEY and GROQ_API_KEY (or OPENAI_API_KEY)

# 3. Build and start all services
docker-compose up --build

# 4. Open the web UI
open http://localhost:3000
```

To stop: `docker-compose down`

To follow logs: `docker-compose logs -f [service-name]`

---

## Usage

### Web UI

Navigate to `http://localhost:3000` for the chat interface.

### API

```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the current CPU usage?"}'
```

### Example Queries

**System resources:**
- "What is the current CPU usage?"
- "How much memory is being used?"
- "How much disk space is left?"
- "Give me a full system health report"

**Containers:**
- "What containers are running?"
- "List all Docker containers and their status"
- "Which containers are stopped?"

---

## What the Assistant Can and Cannot Do

### Allowed (Stage 1)

- Report system resource usage (CPU, memory, disk)
- List Docker container status, images, and port mappings
- Answer questions about current system health

### Not Allowed (Stage 1)

- Restart or stop/start containers or services
- Execute shell commands
- Modify the filesystem
- Change firewall or network configuration
- Schedule or automate tasks

Requests for forbidden actions are refused with a clear explanation.

---

## Environment Variables

| Variable | Service | Default | Purpose |
|----------|---------|---------|---------|
| `API_KEY` | Gateway | — | Client authentication (required) |
| `LLM_PROVIDER` | LLM Adapter | `groq` | Provider selection: `groq` or `openai` |
| `GROQ_API_KEY` | LLM Adapter | — | Groq API key (required if using Groq) |
| `OPENAI_API_KEY` | LLM Adapter | — | OpenAI API key (required if `LLM_PROVIDER=openai`) |
| `RATE_LIMIT_REQUESTS` | Gateway | `60` | Max requests per rate-limit window |
| `RATE_LIMIT_WINDOW` | Gateway | `60` | Rate-limit window in seconds |
| `LOG_LEVEL` | All | `INFO` | Log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Development

### Running Tests

```bash
# From the homelab-assistant/ directory
pip install -e ".[dev]"   # or: poetry install
pytest
```

### Linting and Type Checking

```bash
ruff check .
mypy .
```

### Project Layout

```
homelab-assistant/
├── apps/
│   ├── gateway/          # API gateway service
│   ├── orchestrator/     # Assistant orchestration
│   ├── llm_adapter/      # LLM provider abstraction
│   ├── tool_monitoring/  # System metrics service
│   └── frontend/         # React/Vite web UI
├── packages/
│   ├── homelab_schemas/  # Shared Pydantic models
│   └── homelab_common/   # Shared config and logging
├── deploy/               # Docker Compose and .env.example
└── tests/                # Integration and unit tests
```

---

## Extending the Assistant

See [`CLAUDE.md`](../CLAUDE.md) for detailed guidance on:

- **Adding a new LLM provider** — implement the interface in `apps/llm_adapter/providers/base.py`
- **Adding a new tool** — define the schema, register the tool in the orchestrator, and implement the endpoint in the appropriate service

---

## Audit Logging

The orchestrator writes append-only JSONL audit logs to `/var/log/homelab-assistant/audit.jsonl` (persisted via Docker volume). Each entry contains: timestamp, conversation ID, user message, assistant response, and any tool calls made.
