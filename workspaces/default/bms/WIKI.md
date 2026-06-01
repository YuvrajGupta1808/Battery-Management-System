# BMS Remote Wiki — Schema Pointer

> **Master schema on Tigris:** `dev/default/schema/WIKI.md` in bucket `canary-bms-knowledge`  
> Pattern: [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

Wiki markdown is **remote only** on [Tigris](https://t3.storage.dev). Do not create `bms/knowledge/` locally.

## Three layers

| Layer | Location | Who writes |
|-------|----------|------------|
| Raw sources (PDFs) | Tigris `dev/default/raw/` | User uploads; agent never edits |
| Wiki (markdown) | Tigris `dev/default/wiki/` | Agent maintains |
| Schema | Tigris `dev/default/schema/WIKI.md` + this file | Co-evolved |

## Agent operations

### Query (scope, standards, datasheets, coding conventions)
1. Tigris MCP: read `dev/default/wiki/index.md`
2. Read linked pages under `dev/default/wiki/`
3. Cite wiki paths in answers
4. Optionally file new synthesis pages

### Ingest (new PDF)
1. Upload PDF to `dev/default/raw/<category>/`
2. Write `dev/default/wiki/sources/<slug>.md` (1:1 summary)
3. Update `entities/`, `concepts/` as needed
4. Append `dev/default/wiki/log.md`; refresh `index.md`

### Diagram design
- Follow [`SKILL.md`](SKILL.md) for architecture/rules
- When thresholds need standards justification → **query remote wiki first**

## Local artifacts (only these)
- `bms/architecture.bms.json`
- `bms/safety_rules.yaml`
- `bms/templates/` (read-only)

## Tools
- **Cursor / workbench:** Tigris MCP (`list objects`, `create file`, upload, download)
- **Bootstrap:** `make tigris-bootstrap`
- **Verify:** `make tigris-probe`
