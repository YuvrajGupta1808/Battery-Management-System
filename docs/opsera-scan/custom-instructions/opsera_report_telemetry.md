# CANary — opsera_report_telemetry

Call automatically after other Opsera tools complete (phase 5 of security-scan, or end of architecture/compliance runs).

## Defaults

```yaml
toolName: <matching parent tool, e.g. opsera_security_scan>
status: success | partial | failed
target: CANary/Battery-Management-System
targetType: repository
repoUrl: <from git remote if available>
executionId: <_execution_id from phased session if present>
```

## Rules

- Always report honest counts — never zero-out failed scans.
- Include `categories` and `metadata.scannersRun` for security-scan.
- Upload report file when phase 4 produced HTML/MD (`reportFileName`).