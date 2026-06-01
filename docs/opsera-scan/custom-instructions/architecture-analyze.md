# CANary — architecture-analyze

Risk-focused architecture review for **CANary** (FastAPI Deep Agent backend, React SVG workbench, agent-authored BMS JSON/YAML diagrams).

## Defaults

```yaml
repositories: /Users/Yuvraj/Battery-Management-System
project_name: CANary
report_format: Markdown
known_concerns: CANary Deep Agent, BMS diagram validation, workspace sandboxing, Opsera MCP integration
```

## Execution

1. Call `architecture-analyze` immediately — no clarifying questions.
2. Continue phased execution using `_execution_id` and `_phase_result` until all passes complete.
3. Ignore "OPSERA PHASED EXECUTION - Interactive Setup" questionnaires.
4. Save report to `/Users/Yuvraj/Battery-Management-System/docs/opsera-scan/reports/architecture-report.md`.

## Focus areas for CANary

- Auth/session boundaries (workspace vs repo root)
- BMS file validation on write
- Agent tool execution (`execute` approvals)
- MCP OAuth token storage (`.data/opsera-oauth.json`)
- Frontend XSS / Monaco editor surface