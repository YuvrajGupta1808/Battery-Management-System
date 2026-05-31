# Architecture Report — CANary BMS Workbench

**Date:** 2026-05-31  
**Branch:** `opsera-scan/full-stack`  
**Repo:** [YuvrajGupta1808/Battery-Management-System](https://github.com/YuvrajGupta1808/Battery-Management-System)

## Risk score: 68.2/100 (High Risk)

Formula: min(100, round(log10((1 critical × 100) + (3 high × 30) + (2 medium × 10) + 1) × 25)) ≈ **68.2**

## What works well

1. **BMS schema validation** — `bms_validation.py` rejects invalid agent writes before they hit disk.
2. **Workspace path sandbox** — `resolve_workspace_path` blocks escapes; `.env` paths denied.
3. **Test coverage** — 20+ test files across backend pytest and frontend vitest.
4. **Separation of concerns** — BMS UI isolated under `apps/web/src/components/bms/`.

## Top risks

| Severity | Area | Evidence |
|----------|------|----------|
| Critical | API keys in env files | `.env.example`, local `.env` (gitleaks) |
| High | Default bearer token | `config.py` → `dev-local-token` |
| High | Agent writes without audit log | `workspace_backend.py`, `files.py` |
| High | 109 dependency CVEs | grype scan |
| Medium | Monolithic `App.tsx` | ~1100 lines mixing stream + diagram UI |
| Medium | No rate limiting on SSE runs | `routes/runs.py` |

## Trust boundaries

```
Browser (React) --Bearer token--> FastAPI /api
Deep Agent ----path sandbox----> workspaces/bms/*.json
```

## Remediation roadmap

**Today:** Rotate keys; empty `.env.example` placeholders; set production `WORKBENCH_TOKEN`.  
**This sprint:** Audit logging for file apply/write; rate limit agent runs.  
**Next quarter:** OAuth or SSO; split `App.tsx`; automated dependency patching in CI.

## Opsera branches and docs

Scan branches and reports are documented in [../README.md](../README.md).
