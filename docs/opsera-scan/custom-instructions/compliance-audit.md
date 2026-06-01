# CANary — compliance-audit

Run immediately. Do not quiz the user.

## Defaults

```yaml
framework: soc2
scope: full
evidence_collection: hybrid
output_format: detailed
include_remediation: true
repositories: /Users/Yuvraj/Battery-Management-System
```

## Execution

1. Call `compliance-audit` and continue all passes via `_execution_id` / `_phase_result`.
2. Ignore interactive setup banners.
3. Save report under `/Users/Yuvraj/Battery-Management-System/docs/opsera-scan/reports/` (e.g. `compliance-report-soc2.md`).
4. Map each gap to a concrete CANary fix (config, docs, code).

## CANary context

- Local-first workbench; secrets in `.env` (gitignored)
- Opsera OAuth tokens in `.data/` (gitignored)
- BMS safety rules are domain logic, not infosec controls — focus on app/platform controls