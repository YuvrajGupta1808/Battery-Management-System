# Opsera Scan — CANary

Hackathon integration with [Opsera DevSecOps Agents](https://docs.agents.opsera.ai/) via MCP in Cursor.

## Contents

| Path | Description |
|------|-------------|
| [SETUP.md](SETUP.md) | MCP setup and sample chat prompts |
| [reports/](reports/) | Security, architecture, and SOC2 audit outputs |

## Git branches (scan demo)

| Branch | Contents |
|--------|----------|
| `opsera-scan/bms-backend` | FastAPI validation, workspace agent tools, tests |
| `opsera-scan/bms-frontend` | BMS SVG renderer, workbench UI |
| `opsera-scan/platform-config` | README, env example, Opsera docs |
| `opsera-scan/full-stack` | Merge of backend + frontend + platform |
| `opsera-scan/reports` | Full stack + scan reports under `docs/opsera-scan/reports/` |

## Run scans in Cursor

1. Enable Opsera in **Settings → Tools and MCP** (see [SETUP.md](SETUP.md))
2. In Agent chat:

```
Run a security scan on this repository. Report critical and high findings.
```

```
Analyze CANary architecture: agent-authored BMS diagrams, FastAPI backend, React SVG renderer.
```

```
Run a SOC2 compliance audit on this codebase.
```
