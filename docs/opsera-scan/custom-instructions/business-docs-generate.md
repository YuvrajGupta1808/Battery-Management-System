# CANary — business-docs-generate

Generate stakeholder-facing docs from the CANary codebase.

## Defaults

```yaml
repositories: /Users/Yuvraj/Battery-Management-System
project_name: CANary
document_types: All (recommended)
output_format: Markdown
focus: BMS validation workbench, agent-authored circuit diagrams, safety rule inspection
```

## Execution

1. Call `business-docs-generate` immediately — no clarifying questions.
2. Continue phased execution until complete.
3. Save Markdown outputs under `/Users/Yuvraj/Battery-Management-System/docs/opsera-scan/reports/` or `/Users/Yuvraj/Battery-Management-System/docs/`.
4. Describe CANary as a BMS **validation engineer workbench**, not generic IDE.

## Mode B (feature trace)

If user names a flow (e.g. "agent writes BMS diagram"), set `functionality_to_trace` and run trace mode.