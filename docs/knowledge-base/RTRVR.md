# Retriever AI (rtrvr.ai) → Tigris Wiki (batch only)

**rtrvr.ai is not wired into the CANary agent.** It is a one-way ingest pipeline: fetch BMS info from URLs → compile markdown → upload to Tigris.

The workbench agent reads the **Tigris wiki** (MCP). It never calls rtrvr directly.

## Flow

```
You / CI:  make rtrvr-sync
              │
              ▼
       POST api.rtrvr.ai/agent   (collect only)
              │
              ▼
       Tigris: raw/rtrvr/*.json + wiki/sources/*.md + wiki/entities/*.md
              │
              ▼
       Agent: reads Tigris wiki/index.md (MCP) when designing BMS
```

## Setup

```bash
# .env
RTRVR_API_KEY=rtrvr_...
```

## Commands

```bash
make rtrvr-sync          # live fetch → compile → Tigris
make rtrvr-sync-offline  # use /tmp/rtrvr-*.json cache
```

## Cataloged BMS jobs

| Job | Source URL | Tigris wiki output |
|-----|------------|-------------------|
| `bq76952-ti` | ti.com/product/BQ76952 | `wiki/sources/bq76952-rtrvr-ti.md`, `wiki/entities/bq76952.md` |
| `ltc6811-adi` | analog.com LTC6811 | `wiki/sources/ltc6811-rtrvr-adi.md`, `wiki/entities/ltc6811.md` |
| `tigris-mcp-docs` | tigrisdata.com MCP docs | `wiki/sources/tigris-mcp-rtrvr.md` |
| `bms-wikipedia` | Wikipedia BMS | `wiki/sources/bms-wikipedia-rtrvr.md`, `wiki/concepts/bms-fundamentals.md` |

Implementation: [`backend/src/agent_workbench/scripts/rtrvr_sync.py`](../../backend/src/agent_workbench/scripts/rtrvr_sync.py)
