"""Sync rtrvr.ai retrievals → compile wiki pages → upload to Tigris."""

from __future__ import annotations

from typing import Any

import argparse
import json
import textwrap
from datetime import UTC, datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from agent_workbench.infra.rtrvr_client import (
    RtrvrSettings,
    agent_run,
    extract_result_text,
    get_rtrvr_settings,
)
from agent_workbench.infra.tigris_storage import get_text, get_tigris_settings, list_prefix, put_bytes, put_text

NOW = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

# BMS retrieval jobs: id → (urls, prompt, wiki paths)
RETRIEVAL_JOBS: dict[str, dict] = {
    "bq76952-ti": {
        "urls": ["https://www.ti.com/product/BQ76952"],
        "prompt": (
            "Extract BQ76952 battery monitor specs for BMS design: series cell count min/max, "
            "communication interfaces, balancing type, integrated protections, supported chemistries, "
            "package. Return structured data."
        ),
        "wiki_source": "wiki/sources/bq76952-rtrvr-ti.md",
        "wiki_entity": "wiki/entities/bq76952.md",
        "tags": ["datasheet", "ti", "bq76952", "rtrvr"],
    },
    "ltc6811-adi": {
        "urls": ["https://www.analog.com/en/products/ltc6811.html"],
        "prompt": (
            "Extract LTC6811 multicell battery monitor specs: cells per IC, isoSPI interface, "
            "ADC resolution, balancing, EV/ESS applications. Return markdown tables."
        ),
        "wiki_source": "wiki/sources/ltc6811-rtrvr-adi.md",
        "wiki_entity": "wiki/entities/ltc6811.md",
        "tags": ["datasheet", "adi", "ltc6811", "rtrvr"],
    },
    "tigris-mcp-docs": {
        "urls": ["https://www.tigrisdata.com/docs/ai/mcp-server/"],
        "prompt": (
            "Summarize Tigris MCP server for AI agents: bucket ops, object CRUD, presigned URLs, "
            "install with npx @tigrisdata/tigris-mcp-server. Markdown for BMS knowledge base."
        ),
        "wiki_source": "wiki/sources/tigris-mcp-rtrvr.md",
        "wiki_entity": None,
        "tags": ["tigris", "mcp", "rtrvr"],
    },
    "bms-wikipedia": {
        "urls": ["https://en.wikipedia.org/wiki/Battery_management_system"],
        "prompt": (
            "Explain BMS functions for engineers: cell monitoring, protection, balancing, "
            "SOC/SOH, thermal management, topology. Structured markdown."
        ),
        "wiki_source": "wiki/sources/bms-wikipedia-rtrvr.md",
        "wiki_concept": "wiki/concepts/bms-fundamentals.md",
        "tags": ["reference", "bms", "rtrvr"],
    },
}


def _source_page(
    job_id: str,
    job: dict,
    response: dict[str, Any],
    *,
    extracted: str,
) -> str:
    traj = response.get("trajectoryId", "unknown")
    credits = (response.get("usage") or {}).get("creditsUsed", "?")
    urls = ", ".join(job.get("urls") or [])
    return textwrap.dedent(f"""\
        # Source: rtrvr retrieval — {job_id}

        > **Retrieved:** {NOW}
        > **rtrvr trajectory:** `{traj}`
        > **URLs:** {urls}
        > **Credits used:** {credits}
        > **Tags:** {", ".join(job.get("tags") or [])}

        ## Extracted content (rtrvr.ai agent)

        {extracted}

        ## Raw JSON archive

        Stored at `raw/rtrvr/{job_id}.json` on Tigris.

        ## CANary usage

        Agent reads this page via `wiki/index.md` → compile into `safety_rules.yaml` thresholds and `architecture.bms.json` part selection.
        """)


def _bq76952_entity_from_json(data: dict) -> str:
    sc = data.get("series_cells") or {}
    prot = data.get("protections") or {}
    ifaces = ", ".join(data.get("communication_interfaces") or [])
    chems = ", ".join(data.get("supported_chemistries") or [])
    return textwrap.dedent(f"""\
        # BQ76952 — TI Battery Monitor AFE (rtrvr-enriched)

        > PDF: `raw/datasheets/bq76952.pdf` | rtrvr: `wiki/sources/bq76952-rtrvr-ti.md`
        > Last updated: {NOW}

        ## Specs (from TI via rtrvr.ai)

        | Parameter | Value |
        |-----------|-------|
        | Series cells | {sc.get('min', '?')}–{sc.get('max', '?')} |
        | Interfaces | {ifaces} |
        | Balancing | {data.get('balancing_type', '—')} |
        | Package | {data.get('package', '—')} |
        | Chemistries | {chems} |

        ## Protections
        {prot.get('details', json.dumps(prot))}

        ## CANary schematic
        - Node: `cell_monitor_ic`, `components.cell_monitor_0.part`: `"BQ76952"`
        - Use for ≤{sc.get('max', 16)}S packs
        - MCU via I2C (primary) or SPI/HDQ

        ## Threshold defaults (verify chemistry)
        | Chemistry | OVP | UVP |
        |-----------|-----|-----|
        | NMC / Li-ion | 4.25 V | 2.5 V |
        | LFP / LiFePO4 | 3.65 V | 2.5 V |

        ## Related
        - [protection-systems](../concepts/protection-systems.md)
        - [topology-series-parallel](../concepts/topology-series-parallel.md)
        """)


def _ltc6811_entity_from_text(text: str) -> str:
    return textwrap.dedent(f"""\
        # LTC6811 — ADI Multicell Monitor (rtrvr-enriched)

        > rtrvr source: `wiki/sources/ltc6811-rtrvr-adi.md`
        > Last updated: {NOW}

        {text}

        ## CANary
        - Use when series >16 or user specifies isoSPI / LTC6811
        - Two `cell_monitor_ic` nodes for 24S
        - Split CELL pins per IC block
        """)


def _bms_fundamentals_from_text(text: str) -> str:
    return textwrap.dedent(f"""\
        # BMS Fundamentals

        > Source: Wikipedia via rtrvr.ai — `wiki/sources/bms-wikipedia-rtrvr.md`
        > Last updated: {NOW}

        {text}
        """)


def _build_index(existing: str | None) -> str:
    base = existing or ""
    extra = textwrap.dedent(f"""

        ## rtrvr.ai retrievals ({NOW.split()[0]})
        - [bq76952-rtrvr-ti](sources/bq76952-rtrvr-ti.md) — TI product page extraction
        - [ltc6811-rtrvr-adi](sources/ltc6811-rtrvr-adi.md) — ADI product page extraction
        - [tigris-mcp-rtrvr](sources/tigris-mcp-rtrvr.md) — Tigris MCP docs extraction
        - [bms-wikipedia-rtrvr](sources/bms-wikipedia-rtrvr.md) — BMS fundamentals
        - [bms-fundamentals](concepts/bms-fundamentals.md) — compiled concept page
        """)
    if "bq76952-rtrvr-ti" in base:
        return base
    return base.rstrip() + extra


def _update_manifest(existing_yaml: str | None, jobs_done: list[dict]) -> str:
    data = yaml.safe_load(existing_yaml) if existing_yaml else {}
    if not isinstance(data, dict):
        data = {}
    kb = data.setdefault("knowledge_base", {})
    kb["rtrvr_enabled"] = True
    docs: list = list(data.get("documents") or [])
    known = {d.get("id") for d in docs if isinstance(d, dict)}
    for row in jobs_done:
        if row["id"] in known:
            continue
        docs.append(row)
    data["documents"] = docs
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def run_job(
    settings: RtrvrSettings,
    job_id: str,
    job: dict,
    *,
    live: bool = True,
    cache_dir: Path | None = None,
) -> tuple[dict[str, Any], str]:
    response: dict[str, Any]
    cache_path = (cache_dir or Path("/tmp")) / f"rtrvr-{job_id}.json"
    aliases = {
        "bq76952-ti": ["bq76952-ti", "bq76952"],
        "ltc6811-adi": ["ltc6811-adi", "ltc6811"],
        "tigris-mcp-docs": ["tigris-mcp-docs", "tigris-mcp"],
        "bms-wikipedia": ["bms-wikipedia", "bms-wiki"],
    }
    if live and settings.configured:
        response = agent_run(settings, input_text=job["prompt"], urls=job.get("urls"))
        cache_path.write_text(json.dumps(response, indent=2), encoding="utf-8")
    else:
        response = None
        for alias in aliases.get(job_id, [job_id]):
            candidate = (cache_dir or Path("/tmp")) / f"rtrvr-{alias}.json"
            if candidate.is_file():
                response = json.loads(candidate.read_text(encoding="utf-8"))
                break
        if response is None:
            raise RuntimeError(f"No cache for {job_id} and rtrvr not configured")

    extracted = extract_result_text(response)
    return response, extracted


def sync_all(*, live: bool = True, job_ids: list[str] | None = None) -> dict:
    tigris = get_tigris_settings()
    rtrvr = get_rtrvr_settings()
    if not tigris.configured:
        raise RuntimeError("Tigris not configured")

    ids = job_ids or list(RETRIEVAL_JOBS.keys())
    jobs_done: list[dict] = []
    uploaded: list[str] = []
    skipped: list[str] = []

    for job_id in ids:
        job = RETRIEVAL_JOBS[job_id]
        try:
            response, extracted = run_job(rtrvr, job_id, job, live=live)
        except RuntimeError as exc:
            skipped.append(f"{job_id}: {exc}")
            continue

        # Archive raw JSON on Tigris
        raw_key = f"raw/rtrvr/{job_id}.json"
        put_bytes(tigris, raw_key, json.dumps(response, indent=2).encode(), content_type="application/json")
        uploaded.append(raw_key)

        # Source page
        source_rel = job["wiki_source"]
        put_text(tigris, source_rel, _source_page(job_id, job, response, extracted=extracted))
        uploaded.append(source_rel)

        jobs_done.append(
            {
                "id": job_id,
                "title": job_id.replace("-", " ").title(),
                "type": "rtrvr-retrieval",
                "raw_json": raw_key,
                "wiki_source": source_rel,
                "wiki_entity": job.get("wiki_entity"),
                "rtrvr_trajectory": response.get("trajectoryId"),
                "tags": job.get("tags"),
            }
        )

        # Entity / concept enrichment
        result = response.get("result") or {}
        if job_id == "bq76952-ti" and isinstance(result.get("json"), dict):
            put_text(tigris, "wiki/entities/bq76952.md", _bq76952_entity_from_json(result["json"]))
            uploaded.append("wiki/entities/bq76952.md")
        elif job_id == "ltc6811-adi":
            put_text(tigris, "wiki/entities/ltc6811.md", _ltc6811_entity_from_text(extracted))
            uploaded.append("wiki/entities/ltc6811.md")
        elif job_id == "bms-wikipedia" and job.get("wiki_concept"):
            put_text(tigris, job["wiki_concept"], _bms_fundamentals_from_text(extracted))
            uploaded.append(job["wiki_concept"])

    # Pipeline doc update
    pipeline = get_text(tigris, "wiki/ingest-pipeline.md") or ""
    if "rtrvr.ai" not in pipeline:
        pipeline += textwrap.dedent(f"""

            ## rtrvr.ai retrieval layer ({NOW})

            1. `POST https://api.rtrvr.ai/agent` with `input` + `urls`
            2. Archive JSON → `raw/rtrvr/<job-id>.json`
            3. Compile → `wiki/sources/<job-id>.md`
            4. Update entities/concepts + manifest

            Run: `make rtrvr-sync`
            """)
        put_text(tigris, "wiki/ingest-pipeline.md", pipeline)
        uploaded.append("wiki/ingest-pipeline.md")

    index = _build_index(get_text(tigris, "wiki/index.md"))
    put_text(tigris, "wiki/index.md", index)
    uploaded.append("wiki/index.md")

    manifest = _update_manifest(get_text(tigris, "manifest.yaml"), jobs_done)
    put_text(tigris, "manifest.yaml", manifest, content_type="text/yaml")
    uploaded.append("manifest.yaml")

    log = get_text(tigris, "wiki/log.md") or "# Log\n"
    put_text(
        tigris,
        "wiki/log.md",
        log.rstrip() + f"\n\n## [{NOW.split()[0]}] rtrvr-sync | {len(ids)} retrievals → Tigris wiki\n",
    )
    uploaded.append("wiki/log.md")

    return {"jobs": len(jobs_done), "skipped": skipped, "uploaded": uploaded, "trajectories": [j.get("rtrvr_trajectory") for j in jobs_done]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rtrvr.ai → Tigris wiki sync")
    parser.add_argument("--offline", action="store_true", help="Use /tmp/rtrvr-*.json cache only")
    parser.add_argument("--job", action="append", dest="jobs", help="Single job id")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[4]
    load_dotenv(repo / ".env")

    result = sync_all(live=not args.offline, job_ids=args.jobs)
    print(yaml.safe_dump(result, sort_keys=False))

    if args.verify:
        tigris = get_tigris_settings()
        keys = [k for k in list_prefix(tigris) if "rtrvr" in k or "bms-fundamentals" in k]
        print("verify keys:", len(keys))
        for k in sorted(keys)[:20]:
            print(" ", k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
