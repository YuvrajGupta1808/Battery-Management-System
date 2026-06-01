"""Bootstrap Karpathy-style BMS wiki on Tigris (remote only — no local wiki files)."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from agent_workbench.infra.tigris_storage import get_tigris_settings, list_prefix, put_text

NOW = datetime.now(UTC).strftime("%Y-%m-%d")

SEED_FILES: dict[str, str] = {
    "wiki/index.md": f"""# CANary BMS Wiki Index

> Remote wiki on Tigris — agent-maintained ([Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f))
> Last bootstrap: {NOW}

## Scope
- [project-scope](scope/project-scope.md) — CANary product scope and success criteria
- [user-scope](scope/user-scope.md) — personas and user journeys

## Engineering
- [coding-conventions](engineering/coding-conventions.md) — how we write code in this repo
- [repo-layout](engineering/repo-layout.md) — local vs remote artifact split

## Reference
- [overview](overview.md) — BMS + CANary high-level overview
- [synthesis](synthesis.md) — evolving cross-document thesis

## Categories (empty until ingest)
- `concepts/` — BMS concepts (SOC, thermal runaway, …)
- `entities/` — parts (BQ76952, LTC6811, …)
- `sources/` — 1:1 page per ingested PDF
""",
    "wiki/log.md": f"""# CANary BMS Wiki Log

Append-only timeline. Prefix entries: `## [YYYY-MM-DD] ingest|query|lint | title`

## [{NOW}] bootstrap | Initial wiki skeleton
Created index, scope, engineering pages, schema, manifest on Tigris.
""",
    "wiki/overview.md": """# CANary BMS Overview

CANary is an agentic Battery Management System validation workbench.

- **Agent** authors `architecture.bms.json` and `safety_rules.yaml` (local workspace)
- **UI** renders interactive SVG schematics
- **Wiki** (this bucket) holds scope, standards, datasheets, research — remote on Tigris
- **Query path:** read `wiki/index.md` first, then drill into linked pages
""",
    "wiki/synthesis.md": """# Evolving Synthesis

Cross-document thesis — updated by the agent as sources are ingested.

## Current thesis (seed)

BMS design in CANary combines agent-authored structured diagrams with a remote compounding wiki.
Standards and datasheets inform safety thresholds; the wiki compiles knowledge once instead of re-deriving from PDFs every query.
""",
    "wiki/scope/project-scope.md": """# CANary Project Scope

## In scope
- Agent-authored BMS diagrams (`architecture.bms.json`, `safety_rules.yaml`)
- SVG circuit renderer with drill-down
- Remote wiki on **Tigris** (scope, standards, datasheets, coding conventions)
- Opsera DevSecOps scans (optional)

## Out of scope (hackathon)
- Full pack simulation runtime
- Production ECU firmware flashing
- Formal certification sign-off

## Success criteria
1. User describes pack → valid architecture + rules in one turn
2. Agent queries remote wiki for standards/datasheet thresholds
3. Knowledge compounds on Tigris across sessions
""",
    "wiki/scope/user-scope.md": """# User Scope & Personas

## Personas
1. **BMS hardware engineer** — topology, AFE/MCU selection, pin-level wiring
2. **Validation engineer** — protection thresholds, fault scenarios, traceability
3. **Hackathon judge** — sponsor demo (Tigris remote wiki, Retriever search)

## Journeys
| User says | Agent does |
|-----------|------------|
| New pack design | Read local SKILL + templates → write architecture + rules |
| Standards question | Read Tigris `wiki/index.md` → relevant pages → cite in answer |
| Add PDF | Upload to `raw/` → ingest → update wiki `sources/` + entities |
""",
    "wiki/engineering/coding-conventions.md": """# Coding Conventions (CANary repo)

## General
- Minimize scope — smallest correct diff
- Match existing naming and patterns in surrounding code
- Business logic out of API route handlers
- Schema-backed objects over loose dicts

## Backend (`backend/src/agent_workbench/`)
- Python 3.12, FastAPI
- Infra in `infra/`, domain in `domain/`, routes thin
- Tests in `backend/tests/`

## Frontend (`apps/web/`)
- React + TypeScript, pnpm workspace
- BMS renderer in `components/bms/`

## Agent artifacts
- **Local:** `bms/architecture.bms.json`, `bms/safety_rules.yaml`
- **Remote (Tigris):** all wiki markdown — never commit wiki pages to git
""",
    "wiki/engineering/repo-layout.md": """# Repository Layout vs Tigris Wiki

## Local (`workspaces/default/`)
```
bms/architecture.bms.json   # diagram (agent)
bms/safety_rules.yaml       # rules (agent)
bms/SKILL.md                # diagram authoring
bms/WIKI.md                 # schema pointer → remote wiki
bms/templates/              # read-only templates
```

## Remote Tigris (`canary-bms-knowledge/dev/default/`)
```
raw/          # immutable PDFs
wiki/         # agent-maintained markdown wiki
schema/       # WIKI.md master schema
manifest.yaml # raw ↔ wiki ↔ retriever ids
```
""",
    "schema/WIKI.md": """# BMS Wiki Schema (remote master)

Karpathy LLM Wiki pattern for CANary BMS knowledge.

## Layers
1. **raw/** — immutable source PDFs (never edit)
2. **wiki/** — agent-written markdown (index, entities, concepts, sources)
3. **schema/WIKI.md** — this file

## Operations
- **Ingest:** PDF → raw/ → update wiki/sources/, entities/, concepts/ → log.md → index.md
- **Query:** index.md → linked pages → answer; file good answers back to wiki
- **Lint:** contradictions, stale pages, orphan links

## Rules
- Never store wiki markdown in the local git repo
- Read index.md before answering scope/standards questions
""",
    "manifest.yaml": """version: "1.0"
knowledge_base:
  name: canary-bms-default
  bucket: canary-bms-knowledge
  prefix: dev/default
  retriever_kb_id: null

documents: []
""",
    "raw/.keep": "",
    "raw/standards/.keep": "",
    "raw/datasheets/.keep": "",
    "raw/research/.keep": "",
    "wiki/concepts/.keep": "",
    "wiki/entities/.keep": "",
    "wiki/sources/.keep": "",
}


def bootstrap(*, dry_run: bool = False) -> list[str]:
    settings = get_tigris_settings()
    if not settings.configured:
        raise RuntimeError("Tigris not configured — set AWS_ACCESS_KEY_ID in .env")

    uploaded: list[str] = []
    for rel, content in SEED_FILES.items():
        key = settings.object_key(rel)
        if dry_run:
            uploaded.append(key)
            continue
        put_text(settings, rel, content, content_type=_content_type(rel))
        uploaded.append(key)
    return uploaded


def _content_type(path: str) -> str:
    if path.endswith(".yaml"):
        return "text/yaml"
    return "text/markdown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap CANary BMS wiki on Tigris")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true", help="List objects under prefix")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[4]
    load_dotenv(repo_root / ".env")

    settings = get_tigris_settings()
    if args.list:
        for key in list_prefix(settings):
            print(key)
        return 0

    keys = bootstrap(dry_run=args.dry_run)
    print(f"{'Would upload' if args.dry_run else 'Uploaded'} {len(keys)} objects to s3://{settings.bucket}/")
    for key in keys:
        print(f"  {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
