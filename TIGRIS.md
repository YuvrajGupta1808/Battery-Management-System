# Tigris configuration (CANary BMS)

Project context for agents working with [Tigris object storage](https://www.tigrisdata.com/docs/get-started/).

## Connection

| Variable | Value |
|----------|-------|
| Endpoint | `https://t3.storage.dev` |
| Region | `auto` |
| Bucket | `canary-bms-knowledge` |
| Prefix | `dev/default` |

Credentials: `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in `.env` (from [storage.new/accesskey](https://storage.new/accesskey)).

## Remote wiki layout

```
canary-bms-knowledge/dev/default/
  raw/           # immutable PDFs
  wiki/          # Karpathy LLM Wiki (agent-maintained)
  schema/        # WIKI.md master
  manifest.yaml  # catalog
```

## MCP

- Cursor: `scripts/tigris-mcp.sh` (loads `.env`, runs `@tigrisdata/tigris-mcp-server`)
- Backend: `backend/src/agent_workbench/infra/tigris_mcp.py`

## Skills

```bash
npx skills add tigrisdata/skills
```

## Commands

```bash
make tigris-bootstrap   # seed remote wiki skeleton
make tigris-probe       # list wiki objects + optional MCP probe
```
