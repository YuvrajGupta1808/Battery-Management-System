# Opsera MCP Setup for CANary

CANary uses [Opsera DevSecOps Agents](https://docs.agents.opsera.ai/) via MCP.

Opsera’s docs: **no API keys required for IDE MCP** — you sign in with Google in the browser and the IDE handles auth automatically.

## Cursor (already works for you)

1. Sign in at [agent.opsera.ai](https://agent.opsera.ai)
2. Project config: `.cursor/mcp.json` (no token — just the URL)
3. **Cursor Settings** → **Tools and MCP** → enable **opsera**
4. Cursor opens the browser yes/no consent flow on first use

```json
{
  "mcpServers": {
    "opsera": {
      "type": "streamable-http",
      "url": "https://agent.opsera.ai/mcp"
    }
  }
}
```

Use Opsera in **Cursor Agent chat** for scans anytime — no `.env` token needed.

## CANary Deep Agent workbench (separate process)

The CANary **backend** is not Cursor. It cannot reuse Cursor’s saved browser session. Two options:

### Option A — Browser login (recommended, no API token)

Same Google sign-in as Cursor, one-time from the terminal:

```bash
make opsera-login
```

This opens your browser, completes Opsera OAuth, and saves tokens to `.data/opsera-oauth.json`. Restart the backend afterward.

The Deep Agent then connects via [langchain-mcp-adapters](https://docs.langchain.com/oss/python/langchain/mcp) `MultiServerMCPClient` with MCP OAuth (not a manual bearer token).

### Option B — Optional API token

If your Opsera portal provides an API key, set in `.env`:

```bash
OPSERA_API_TOKEN=your_token
```

Token takes precedence over browser OAuth.

## Tools to run in chat

| Tool | Purpose | CANary chat prompt |
|------|---------|-------------------|
| `security-scan` | SAST, secrets, containers, IaC | Run a security scan on this repository |
| `architecture-analyze` | Risk-focused system design review | Analyze CANary architecture |
| `compliance-audit` | SOC2 / ISO27001 gap analysis | Run a SOC2 compliance audit |
| `business-docs-generate` | FRD/BRD from codebase | Generate business docs from this repo |
| `dora-metrics` | DORA deployment metrics | Generate DORA metrics for this repo |
| `sql-security` | Databricks SQL security scan | Scan SQL security (Databricks) |
| `opsera_report_telemetry` | Analytics telemetry | (called automatically by other tools) |
| `vibe-shift` | Autonomous CI/CD to AWS/EKS | Cursor MCP only — needs cluster + region |

List tools: `make opsera-probe` (no args) or smoke-test: `make opsera-probe` with probe flag in Makefile.

## Sample prompts (Cursor or CANary agent)

```
Run a security scan on this repository. Report critical and high findings.
```

```
Analyze CANary architecture: agent-authored BMS diagrams, FastAPI backend, React SVG renderer.
```

```
Run a SOC2 compliance audit on this codebase.
```

## Scan reports

Outputs are saved under [reports/](reports/) after a full Opsera run.

## Deep Agent — after `make opsera-login`

In the CANary agent chat:

```
Run a security scan on this repo. Fix critical/high findings and save reports under docs/opsera-scan/reports/.
```

The agent loads MCP tools + `opsera_prompt_*` helpers, runs phased Opsera workflows, writes reports, and can apply fixes in-repo.
