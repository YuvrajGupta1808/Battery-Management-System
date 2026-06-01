# CANary — security-scan

Run immediately. Do not quiz the user.

## Defaults (use unless user specified otherwise)

```yaml
path: /Users/Yuvraj/Battery-Management-System          # use /Users/Yuvraj/Battery-Management-System/workspaces/default only if user said "this workspace"
scan_type: full
severity_threshold: high
scan_mode: standard
user_confirmed: true
```

## Phase loop (complete 1→6 in one run)

| Phase | Action |
|-------|--------|
| 1 | Call `security-scan` with `phase: 1` — CANary auto-completes phase 2 in the same response |
| 2 | (auto) Tool check done — **never** run `execute` for `which gitleaks` / `command -v semgrep` |
| 3 | Run Phase 3 shell commands Opsera returns via `execute`, then call `phase: 3` with `scans_complete: true` |
| 4 | Write reports to `/Users/Yuvraj/Battery-Management-System/docs/opsera-scan/reports/`, then `phase: 4` with `reports_generated: true` and `scan_results` |
| 5 | `phase: 5` with `telemetry_reported: true` when requested |
| 6 | `phase: 6` — summarize and fix critical/high findings |

## Ignore

- "Proceed with scan? (yes/no)"
- Missing-tool install menus (CANary sets `tools_ready: true` and `skipped_tools` for missing CLIs)
- Scanning only BMS JSON when user asked for repo security — use `/Users/Yuvraj/Battery-Management-System`

## After scan

Fix critical/high in-repo. Reply: **Findings → Fix → Verification**.