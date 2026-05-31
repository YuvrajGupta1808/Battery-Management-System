# Opsera MCP Setup for CANary

CANary uses [Opsera DevSecOps Agents](https://docs.agents.opsera.ai/) via MCP in Cursor.

## Quick setup

1. Sign in at [agent.opsera.ai](https://agent.opsera.ai)
2. Project config: `.cursor/mcp.json` (streamable-http → `https://agent.opsera.ai/mcp`)
3. **Cursor Settings** → **Tools and MCP** → enable **opsera**

Or install from the [Cursor Marketplace](https://cursor.com/marketplace/opsera).

## Tools to run in chat

| Tool | Purpose |
|------|---------|
| `security-scan` | SAST, secrets, containers, IaC |
| `architecture-analyze` | Risk-focused system design review |
| `compliance-audit` | SOC2 / ISO27001 gap analysis |
| `pre-commit-scan` | Scan staged changes before commit |

## Sample prompts

```
Analyze CANary architecture: agent-authored BMS diagrams, FastAPI backend, React SVG renderer.
```

```
Run a security scan on this repository. Report critical and high findings.
```

## Scan reports

Outputs are saved under [reports/](reports/) after a full Opsera run.
