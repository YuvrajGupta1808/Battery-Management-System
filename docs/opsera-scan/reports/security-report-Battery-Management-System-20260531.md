# Security Report — CANary (Battery-Management-System)

**Date:** 2026-05-31  
**Scan type:** full  
**Severity threshold:** high  
**Risk score:** **85.9/100 (Critical Risk)**

Score = min(100, round(log10((7 critical × 100) + (49 high × 30) + (55 medium × 10) + (3 low × 3) + 1) × 25)) = **85.9**

## Executive summary

Opsera full scan (gitleaks, grype, semgrep; checkov/npm-audit limited) found **114 issues** at or above the configured threshold context. Top risks: **API keys in `.env` / `.env.example`**, **109 dependency CVEs via grype**, and **insecure HTTP urllib usage** in backend config.

## Scan coverage

| Scanner | Status |
|---------|--------|
| gitleaks | PASSED — 2 secret findings |
| grype | PASSED — 109 dependency matches |
| semgrep | PASSED — 3 SAST findings |
| checkov | FAILED — no IaC files detected |
| npm audit | FAILED — root package has no lock audit context |
| hadolint | SKIPPED — no Dockerfile |

## Critical & high findings

### Secrets (gitleaks — Information Disclosure)

| File | Issue | Remediation |
|------|-------|-------------|
| `.env.example:12` | FIREWORKS_API_KEY placeholder looks like real key | Use empty placeholders only |
| `.env:12` | FIREWORKS_API_KEY committed locally | Rotate key; ensure `.env` stays gitignored |

### SAST (semgrep)

| File | Rule | Remediation |
|------|------|-------------|
| `backend/.../config.py` | dynamic urllib + insecure http urlopen for Ollama probe | Restrict to localhost; use HTTPS or disable in prod |
| `backend/.../titles.py` | dynamic urllib usage | Validate URLs; block file:// schemes |

### Dependencies (grype)

109 CVE matches across Python/Node transitive deps — prioritize critical/high RCE and auth-bypass packages; run `grype dir:.` and patch lockfiles.

## Architecture-related security notes

- **Auth:** Bearer token on `/api/*` routes; `/health` is unauthenticated (expected for probes).
- **Default token:** `dev-local-token` in config — must change for any non-localhost deploy.
- **CORS:** Configurable origins with credentials enabled — tighten for production.
- **Agent workspace:** File writes sandboxed to `WORKBENCH_ALLOWED_ROOTS` — validate path escape tests stay green.

## Quick wins (this sprint)

1. Remove real-looking keys from `.env.example`; rotate any exposed Fireworks/Tavily keys.
2. Set strong `WORKBENCH_TOKEN` in production Render deploy.
3. Pin and patch dependencies flagged critical/high by grype.
4. Add rate limiting on `/api/sessions/*/runs/stream` SSE endpoint.

## STRIDE summary

| Category | Count (approx) |
|----------|----------------|
| Spoofing | 1 (weak/default bearer token) |
| Tampering | 3 (SAST input/transport issues) |
| Repudiation | 1 (limited audit logging) |
| Information Disclosure | 50+ (secrets + CVEs) |
| Denial of Service | 2 (no rate limits on agent stream) |
| Elevation of Privilege | 2 (agent file write boundary) |
