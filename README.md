# CANary — BMS Validation Workbench

Agentic design, validation, and visualization for Battery Management Systems (BMS). CANary helps engineers describe pack requirements in natural language; the **coding agent authors BMS circuit diagrams** as structured files; the **UI renders them** as interactive SVG schematics with drill-down, safety rule inspection, and auditable artifacts.

## What CANary Does

| Area | Description |
|------|-------------|
| **Agent-authored BMS diagrams** | Agent writes `bms/architecture.bms.json` — topology, ICs, pins, wires, layout |
| **SVG circuit renderer** | Workbench Diagram tab renders agent output as schematic blocks with drill-down |
| **Safety rules** | Agent maintains `bms/safety_rules.yaml`; inspector shows rules on MCU/Memory |
| **Schema validation** | Backend rejects invalid agent writes with actionable errors |
| **Simulation (planned)** | Pack-level scenarios, fault injection, CAN traces |
| **Validation reports (planned)** | Requirements-driven test cases and verification reports |

Engineering thresholds come from **agent-authored configuration** — not hardcoded constants in the UI.

## BMS Workspace Artifacts

The agent creates diagram files at runtime (schema + skill are committed under `workspaces/default/bms/`):

```
workspaces/default/bms/
├── schema/architecture.schema.json   # JSON Schema contract
├── templates/architecture.template.bms.json
├── SKILL.md                          # Agent diagram authoring guide
└── README.md

# Agent-created at runtime:
bms/architecture.bms.json
bms/safety_rules.yaml
```

## Repository Layout

```
Battery-Management-System/
├── backend/              # FastAPI workbench API + BMS file validation
├── apps/web/             # React workbench + SVG BMS circuit diagram renderer
├── workspaces/           # Agent-scoped workspaces
│   └── default/          # BMS schema, skill, templates
├── .data/                # Session and runtime data
└── README.md
```

### Planned modules (future)

| Module | Purpose |
|--------|---------|
| `simulation/` | Scenario runners and fault injection |
| `validation/` | Requirements traceability and test execution |
| `reports/` | Generated verification and analysis reports |

## Quick Start

### Prerequisites

- Python 3.12
- Node.js 20+ and [pnpm](https://pnpm.io/) 10+
- Optional: provider API keys (Fireworks, OpenAI, Anthropic) for live agent runs

### Setup

```bash
cp .env.example .env
.venv/bin/python --version >/dev/null 2>&1 || python3.12 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e "backend[deepagents,test]"
pnpm install
pnpm dev
```

| Service | URL |
|---------|-----|
| **Web UI** | http://127.0.0.1:5173 |
| **API** | http://127.0.0.1:8000 (`/health` → `{"status":"ok"}`) |

Default auth token: `dev-local-token` (set via `WORKBENCH_TOKEN` in `.env`).

The default model is `mock:deterministic`, so the app runs without provider credentials. Set `WORKBENCH_DEFAULT_MODEL` to an allowlisted model (e.g. `openai:accounts/fireworks/models/qwen3p6-plus`) once credentials are configured.

### Workspace configuration

Agent file access is scoped to managed folders under `workspaces/`:

```bash
WORKBENCH_WORKSPACE_ROOT=/path/to/Battery-Management-System/workspaces
WORKBENCH_ALLOWED_ROOTS=/path/to/Battery-Management-System/workspaces
```

BMS product code and documentation should be developed inside `workspaces/default/` (or additional named workspaces).

## Opsera (MCP)

[Opsera DevSecOps Agents](https://docs.agents.opsera.ai/) connect via MCP for in-IDE security scans and architecture analysis. Project config: `.cursor/mcp.json`. Setup, branch strategy, and scan reports: [docs/opsera-scan/](docs/opsera-scan/).

**Deep Agent integration:** Cursor MCP auth does not carry over to the backend. Run `make opsera-login` once (browser Google sign-in, same as Cursor) or set optional `OPSERA_API_TOKEN`. See [docs/opsera-scan/SETUP.md](docs/opsera-scan/SETUP.md).

Quick start: install from [Cursor Marketplace](https://cursor.com/marketplace/opsera), then in chat ask *"Run a security scan on this repository"* or *"Analyze the architecture of CANary"*.

## Tigris remote wiki

BMS scope, standards, datasheets, and coding conventions live on **[Tigris](https://t3.storage.dev)** — not in the local repo ([Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern).

```bash
make tigris-bootstrap   # seed remote wiki on Tigris
make tigris-probe       # verify connectivity + MCP
```

Setup: [docs/knowledge-base/SETUP.md](docs/knowledge-base/SETUP.md). Project config: [TIGRIS.md](TIGRIS.md), schema pointer: `workspaces/default/bms/WIKI.md`.

Enable **tigris** in Cursor MCP. Ask: *"List objects in canary-bms-knowledge"* or *"Read dev/default/wiki/index.md"*.

## Retriever AI (rtrvr.ai)

Browse vendor URLs and compile extractions to Tigris (batch CLI, not an agent tool): [docs/knowledge-base/RTRVR.md](docs/knowledge-base/RTRVR.md).

```bash
make rtrvr-sync
```

## Development

### Run services separately

```bash
# Backend only
PYTHONPATH=backend/src .venv/bin/python -m uvicorn agent_workbench.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend only
pnpm --dir apps/web dev --host 127.0.0.1 --port 5173 --strictPort
```

Or use the Makefile:

```bash
make dev          # both services via pnpm
make test         # backend + frontend tests
```

### Tests

```bash
pnpm test
```

### Enable real Deep Agents (optional)

```bash
cd backend
python3 -m pip install ".[deepagents]"
```

Without `deepagents`, the backend falls back to a deterministic mock agent stream.

## Architecture

```
┌─────────────────┐     SSE/REST      ┌──────────────────┐
│  apps/web       │ ◄──────────────► │  backend/         │
│  (React IDE)    │                   │  (FastAPI)       │
└─────────────────┘                   └────────┬─────────┘
                                               │
                                               ▼
                                      ┌──────────────────┐
                                      │  workspaces/     │
                                      │  BMS source code │
                                      │  docs/wiki       │
                                      └──────────────────┘
```

The workbench streams agent events (thinking, tool calls, file changes, approvals) over SSE. Agents edit files only within allowed workspace roots.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `WORKBENCH_TOKEN` | Bearer token for API auth |
| `WORKBENCH_WORKSPACE_ROOT` | Root directory for managed workspaces |
| `WORKBENCH_ALLOWED_ROOTS` | Paths the agent may read/write |
| `WORKBENCH_DEFAULT_MODEL` | Default LLM model identifier |
| `OPENAI_API_KEY` / `FIREWORKS_API_KEY` | Provider credentials (optional in mock mode) |
| `OPENAI_BASE_URL` | OpenAI-compatible API base URL |

See `.env.example` for the full list.

## Contributing

- Keep business logic out of API route handlers.
- Prefer schema-backed objects over loose dictionaries.
- Treat simulations, reports, CAN traces, and verification results as **auditable artifacts**.
- Update `docs/wiki/` when making durable product or architecture decisions.
