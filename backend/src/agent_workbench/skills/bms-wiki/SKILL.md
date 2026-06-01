---
name: bms-wiki
description: Query remote BMS wiki on Tigris before any factual answer or design decision.
---

# BMS Remote Wiki (Tigris)

Wiki markdown lives **only on Tigris** — never in the local workspace.

## Automatic wiki-first (mandatory)

Do this **before** answering or designing whenever Tigris MCP is online. Users do **not** need to say "read the wiki" or "check Tigris".

1. `tigris_get_object` → `{prefix}/wiki/index.md`
2. Open linked pages under `{prefix}/wiki/` (entities, concepts, sources)
3. Use wiki content for comparisons, thresholds, part selection, and rationale

**Examples:** "BQ76952 vs LTC6811 for 12S LFP", "OVP for NMC", "thermal shutdown" → wiki first, then answer or write files.

## Design requests

Wiki lookup **in parallel** with `/bms/SKILL.md` + templates, then write `architecture.bms.json` and `safety_rules.yaml`.

## Ingest (new PDF)

1. Upload to `{prefix}/raw/`
2. Write `{prefix}/wiki/sources/<slug>.md`
3. Update entities/concepts, `log.md`, `index.md`

## Local vs remote

- **Local:** `architecture.bms.json`, `safety_rules.yaml`, templates, `bms/WIKI.md` (schema pointer)
- **Remote:** everything under `canary-bms-knowledge/dev/default/`

Full schema: read `{prefix}/schema/WIKI.md` on Tigris.
