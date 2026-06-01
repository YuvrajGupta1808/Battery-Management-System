# CANary — sql-security

Databricks SQL security tool. CANary has **no production SQL** — use for repo SQL files only if present.

## Defaults

```yaml
action: scan
sql_file: /Users/Yuvraj/Battery-Management-System
severity_threshold: high
compliance_standard: all
auto_fix: false
```

## Execution

1. If no `.sql` files under `/Users/Yuvraj/Battery-Management-System`, report "no SQL surface" and skip — do not fail the run.
2. Otherwise call `sql-security` with defaults; never ask user for Databricks credentials unless tool errors.
3. Do not confuse with `security-scan` (repo-wide DevSecOps).