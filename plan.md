# Homelab Assistant – Execution Plan  
## Stage 1: Server Monitoring (Read-Only)

---

## Context

This project implements a **private, cloud-first personal assistant** running inside a homelab server (TrueNAS SCALE).
The assistant will interact with internal services and cloud APIs, but **this stage is limited strictly to monitoring and read-only observability**.

The system must be designed so that:
- the LLM is replaceable (cloud now, local later)
- the LLM never executes actions directly
- all sensitive logic, validation, and permissions live in backend code
- no destructive or state-changing operations are allowed in this stage

This document defines **only Stage 1: Monitoring & Observability**.

---

## Stage 1 – Goals (Strict Scope)

### Primary Goal

Allow an authenticated user to query the assistant for **read-only information about the server and services**, such as:
- system health
- resource usage
- container status
- basic logs and alerts

### Explicit Non-Goals (Must NOT be implemented)

The following are **out of scope** and must not be implemented:

- No service restarts
- No container stop/start
- No filesystem changes
- No snapshot creation or deletion
- No firewall, network, or ACL changes
- No shell command execution
- No automation or scheduling

If a user requests any of the above, the assistant must:
- refuse clearly
- explain the limitation
- not attempt partial execution

---

## Architecture Constraints

### High-Level Runtime Components

The system consists of the following components, all running as containers inside the server:

1. Gateway (authentication + HTTPS entrypoint)
2. Orchestrator (assistant core)
3. LLM Adapter (cloud-based, replaceable)
4. Monitoring Tool (read-only)
5. Persistence layer (DB + audit logs)

Only the Gateway may expose a network port.

---

## Repository Structure (Monorepo)

The codebase must follow this structure:

homelab-assistant/
apps/
gateway/ # HTTPS + auth + rate limit
orchestrator/ # assistant core + policies
llm-adapter/ # cloud LLM abstraction
tool-monitoring/ # read-only monitoring tool
packages/
schemas/ # JSON schemas / contracts
common/ # logging, config, utils
deploy/
docker-compose.yml
.env.example
docs/


---

## Component Responsibilities

### 1. Gateway

Responsibilities:
- HTTPS termination
- authentication (token-based or simple login)
- rate limiting
- forwarding requests to the orchestrator

Constraints:
- the only externally reachable service
- no business logic
- no direct access to tools or LLMs

---

### 2. Orchestrator (Assistant Core)

Responsibilities:
- receive user messages
- classify intent (monitoring-only)
- call the LLM Adapter when reasoning is required
- validate all tool calls
- enforce read-only policies
- route tool calls to the Monitoring Tool
- aggregate and format responses
- write audit logs

Hard Rules:
- never execute shell commands
- never call tools not explicitly allowed
- never accept arbitrary parameters without schema validation

---

### 3. LLM Adapter (Cloud-First)

Responsibilities:
- abstract the LLM provider (OpenAI / Gemini / Claude)
- build prompts
- handle tool-calling responses
- return normalized outputs to the orchestrator

Constraints:
- no direct access to tools
- no secrets in prompts
- must be easily replaceable by a local LLM adapter in the future

---

### 4. Monitoring Tool (Read-Only)

This is the only tool implemented in Stage 1.

Responsibilities:
- expose read-only endpoints for:
  - system resource usage (CPU, RAM, disk)
  - container status (running/stopped)
  - basic health checks
  - recent warnings or alerts
- gather data from:
  - Docker API
  - metrics endpoints (if available)
  - local system APIs

Constraints:
- no write operations
- no service control
- no filesystem mutations
- strict allowlist of queries

---

### 5. Persistence & Audit

Two separate concerns must exist:

#### 1. Operational Database
Stores:
- users
- sessions
- configuration
- enabled tools

#### 2. Audit Log (Append-Only)
Stores:
- user request
- interpreted intent
- tool called
- parameters
- result
- timestamp

Audit logs must be append-only and immutable.

---

## Allowed User Queries (Examples)

The assistant must support queries such as:

- "Is everything running correctly?"
- "What containers are currently running?"
- "Is any service unhealthy?"
- "How much disk space is left?"
- "What is the current CPU and memory usage?"
- "Did any service crash recently?"

---

## Forbidden Queries (Must Be Rejected)

Examples include (but are not limited to):

- "Restart the server"
- "Stop a container"
- "Delete a dataset"
- "Change firewall rules"
- "Expose a port"
- "Run this command..."

Rejection rules:
- clear refusal
- explanation of limitation
- no partial execution

---

## Security Requirements

- All secrets must be stored outside of prompts
- Tools must authenticate using internal tokens
- No shell access
- No arbitrary URLs or hosts
- Input validation at all boundaries
- Logs must never include credentials or tokens

---

## Execution Order (Step-by-Step)

1. Create the monorepo structure
2. Implement Gateway with basic authentication
3. Implement Orchestrator skeleton
4. Implement LLM Adapter (cloud provider)
5. Define monitoring schemas (read-only)
6. Implement Monitoring Tool
7. Connect Orchestrator → Tool Router → Monitoring Tool
8. Add audit logging
9. Add refusal logic for non-monitoring requests
10. Manual testing with realistic monitoring queries

---

## Success Criteria for Stage 1

Stage 1 is complete when:

- the assistant answers monitoring queries accurately
- all requests and tool calls are logged
- no destructive action is possible
- the LLM can be replaced without changing orchestrator logic
- the system is safe to use daily

---

## Notes for Future Stages (Informational Only)

Future stages may introduce:
- confirmations
- write-capable tools
- automation
- local LLM execution

These features must NOT be implemented in Stage 1.

