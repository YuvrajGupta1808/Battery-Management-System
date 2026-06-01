# Opsera Custom Instructions (CANary)

Source of truth: `backend/src/agent_workbench/domain/opsera_prompts.py`

Regenerate: `make opsera-instructions`

## Add to Opsera Agent Portal

1. Open [Opsera Agent Portal](https://agent.opsera.ai) → **Custom Instructions**
2. Optional: paste `00-global-canary.md` as a **user-global** instruction (or org-wide in Admin)
3. For each tool below, click **Add Instruction** → scope **By Tool** → select tool name → paste file body

| Portal tool name | File |
|------------------|------|
| (global, optional) | `00-global-canary.md` |
| `security-scan` | `security-scan.md` |
| `architecture-analyze` | `architecture-analyze.md` |
| `compliance-audit` | `compliance-audit.md` |
| `business-docs-generate` | `business-docs-generate.md` |
| `dora-metrics` | `dora-metrics.md` |
| `sql-security` | `sql-security.md` |
| `opsera_report_telemetry` | `opsera_report_telemetry.md` |

Opsera injects these **before tool calls** — they override the default "ask the user" tool descriptions.

## CANary Deep Agent

The backend loads the same text via `opsera_prompts.py` into the agent system prompt and MCP bundle.
After editing prompts, restart the backend and re-run `make opsera-instructions`.
