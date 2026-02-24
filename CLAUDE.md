# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Homelab Assistant is a private, cloud-first personal assistant for homelab servers (TrueNAS SCALE). Currently at **Stage 1: Server Monitoring (Read-Only)** - the assistant can only query system information and must refuse any destructive or state-changing operations.

## Architecture

The system is a Python microservices monorepo with four containerized services:

```
Gateway (8000) → Orchestrator (8001) → LLM Adapter (8002)
                      ↓
               Tool Monitoring (8003)
```

- **Gateway**: HTTPS entrypoint, API key auth, rate limiting. Only externally exposed service.
- **Orchestrator**: Assistant core. Validates tool calls, enforces read-only policies, writes audit logs.
- **LLM Adapter**: Abstracts cloud LLM providers (Groq, OpenAI). Uses provider pattern for future local LLM support.
- **Tool Monitoring**: Read-only system metrics (CPU, memory, disk) and Docker container status.

Services communicate via internal Docker network. Shared code lives in `packages/` (schemas, common utilities).

## Running the Project

```bash
# From deploy/ directory
cp .env.example .env  # Configure API_KEY and GROQ_API_KEY
docker-compose up --build

# View logs
docker-compose logs -f [service-name]

# Stop
docker-compose down
```

Gateway exposes port 8000. Test with:
```bash
curl -X POST http://localhost:8000/chat \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "What containers are running?"}'
```

## Key Directories

- `homelab-assistant/apps/` - Service implementations (each has main.py, Dockerfile, requirements.txt)
- `homelab-assistant/packages/schemas/` - Shared Pydantic models for messages and tools
- `homelab-assistant/packages/common/` - Shared config and logging utilities
- `homelab-assistant/deploy/` - Docker Compose configuration

## Stage 1 Constraints (CRITICAL)

The orchestrator enforces these rules - do not bypass them:

**Allowed**: System health, resource usage, container status, basic logs/alerts

**Forbidden**: Service restarts, container stop/start, filesystem changes, shell execution, firewall/network changes, automation/scheduling

When users request forbidden actions, the assistant must refuse clearly, explain the limitation, and not attempt partial execution.

## Adding New Functionality

**New LLM Provider**: Implement the interface in `apps/llm-adapter/providers/base.py`

**New Tool**:
1. Define tool schema in `packages/schemas/tools.py`
2. Add tool definition to `apps/orchestrator/tools.py`
3. Implement endpoint in appropriate tool service
4. Update orchestrator's tool execution routing

## Shared Package Import Pattern

All services inject the packages directory into Python path:
```python
sys.path.insert(0, "/app/packages")
from schemas import ChatRequest, ChatResponse
from common import setup_logging, Settings
```

## Environment Variables

| Variable | Service | Purpose |
|----------|---------|---------|
| API_KEY | Gateway | Client authentication |
| LLM_PROVIDER | LLM Adapter | Provider selection: "groq" (default) or "openai" |
| GROQ_API_KEY | LLM Adapter | Groq API access (free tier at console.groq.com) |
| OPENAI_API_KEY | LLM Adapter | OpenAI API access (only if LLM_PROVIDER=openai) |
| RATE_LIMIT_REQUESTS | Gateway | Requests per window (default: 60) |
| RATE_LIMIT_WINDOW | Gateway | Window in seconds (default: 60) |
| LOG_LEVEL | All | DEBUG, INFO, WARNING, ERROR |

## Audit Logging

The orchestrator writes append-only JSONL audit logs to `/var/log/homelab-assistant/audit.jsonl` containing: timestamp, conversation_id, user_message, assistant_response, tool_calls.
