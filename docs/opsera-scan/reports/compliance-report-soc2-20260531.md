# SOC2 Compliance Audit — CANary BMS Workbench

**Framework:** SOC2 | **Scope:** full | **Date:** 2026-05-31  
**Overall score:** 62/100 (Partial readiness)

## Control summary

| Category | Status | Score |
|----------|--------|-------|
| Access control | Partial | 55 |
| Encryption / secrets | Partial | 50 |
| Logging & monitoring | Fail | 40 |
| Change management | Partial | 65 |
| Vulnerability management | Partial | 45 |
| Business continuity | Fail | 30 |
| Policies & docs | Partial | 70 |

## Top gaps

1. **CC6.1 Logical access** — Single shared bearer token; default dev token; no MFA/RBAC.
2. **CC6.7 Secrets** — API key patterns in `.env.example`; local `.env` flagged by gitleaks.
3. **CC7.2 Monitoring** — No audit trail for agent file mutations or session changes.

## Passing highlights

- Workspace path sandbox for agent writes
- BMS JSON/YAML schema validation on write
- Backend + frontend automated test suites

## Roadmap to improve score

1. Remove secrets from example env; use secret manager on Render deploy.
2. Add structured audit log for `/files/apply` and agent tool writes.
3. Wire Opsera MCP scans into pre-deploy gate (see [../SETUP.md](../SETUP.md)).
