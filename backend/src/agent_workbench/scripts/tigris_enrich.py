"""Enrich remote BMS wiki on Tigris — concepts, entities, PDFs, manifest, ingest docs."""

from __future__ import annotations

import argparse
import textwrap
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from agent_workbench.infra.tigris_storage import get_tigris_settings, get_text, list_prefix, put_bytes, put_text

NOW = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

# Public datasheet URLs (immutable raw sources)
PDF_SOURCES: dict[str, tuple[str, str]] = {
    "raw/datasheets/bq76952.pdf": (
        "https://www.ti.com/lit/ds/symlink/bq76952.pdf",
        "application/pdf",
    ),
}

ENRICH_MARKDOWN: dict[str, str] = {
    "wiki/ingest-pipeline.md": textwrap.dedent("""\
        # PDF Ingest & Extraction Pipeline

        > How CANary turns BMS PDFs into compounding wiki knowledge on Tigris.

        ## Architecture (Karpathy LLM Wiki + Tigris + optional Retriever)

        ```
        PDF (immutable)          Wiki (compiled)           Query
        ─────────────────        ───────────────           ─────
        raw/datasheets/*.pdf  →  wiki/sources/*.md    →  read index.md first
        raw/standards/*.pdf   →  wiki/entities/*.md       then linked pages
        raw/research/*.pdf    →  wiki/concepts/*.md       Retriever for deep PDF clauses
        ```

        ## Step-by-step ingest (agent workflow)

        | Step | Action | Tigris key |
        |------|--------|------------|
        | 1 | User or script uploads PDF | `raw/<category>/<slug>.pdf` |
        | 2 | Register in manifest | `manifest.yaml` |
        | 3 | Agent reads PDF (MCP download or presigned URL) | — |
        | 4 | Agent writes 1:1 source summary | `wiki/sources/<slug>.md` |
        | 5 | Update entity/concept pages | `wiki/entities/`, `wiki/concepts/` |
        | 6 | Append log, refresh index | `wiki/log.md`, `wiki/index.md` |
        | 7 | (Optional) Retriever ingest for semantic PDF search | external KB |

        ## Extraction template (wiki/sources/*.md)

        Each source page MUST include:
        1. **Header** — PDF path, date, tags
        2. **Scope** — what the document covers
        3. **Key tables** — thresholds, pins, registers (BMS-critical)
        4. **CANary mapping** — how it affects `architecture.bms.json` / `safety_rules.yaml`
        5. **Agent guidance** — when to cite this doc
        6. **Gaps** — what still needs human verification

        ## Why compile to wiki instead of RAG-only?

        - **RAG** re-derives from PDF chunks every query — no accumulation
        - **Wiki** compiles once, cross-links entities, flags contradictions, compounds over time
        - **Tigris** stores both: raw PDF (truth) + wiki markdown (agent index)

        ## Commands

        ```bash
        make tigris-enrich      # upload detailed BMS pages + sample PDFs
        make tigris-probe       # verify objects + MCP
        ```
        """),
    "wiki/concepts/protection-systems.md": textwrap.dedent("""\
        # Protection Systems (BMS)

        ## Functions
        A BMS must detect fault conditions and act within **FTTI** (fault tolerant time interval) for the target ASIL.

        | Protection | Typical trigger (NMC) | Typical trigger (LFP) | CANary rule example |
        |------------|----------------------|----------------------|---------------------|
        | OVP | >4.25 V/cell | >3.65 V/cell | `cell_voltage_max > 4.25` |
        | UVP | <2.5 V/cell | <2.5 V/cell | `cell_voltage_min < 2.5` |
        | OCP charge | pack limit + margin | same | `charge_current > 210` |
        | OCP discharge | pack limit + margin | same | `discharge_current > 250` |
        | OTP | >60 °C discharge | >55 °C | `pack_temp_c > 60` |
        | SCP | dI/dt, fuse, HW comparator | same | contactor open + fuse |

        ## CANary mapping
        - Rules in `safety_rules.yaml` — top-level list, `component: mcu`
        - Link rules to MCU block for UI inspector
        - Always set `description` citing standard or datasheet when user targets certification

        ## Related
        - [thermal-management](thermal-management.md)
        - [entity: BQ76952](../entities/bq76952.md)
        """),
    "wiki/concepts/cell-balancing.md": textwrap.dedent("""\
        # Cell Balancing

        ## Passive balancing
        Bleed resistors on high cells during charge/end-of-charge. BQ76952 integrates balancing FETs.

        ## Active balancing
        Energy transfer between cells — higher efficiency, more complex HW.

        ## CANary
        - `balancing` node in BMS view
        - Rule example: `balance_enable when (cell_delta_mv > 30)`
        - Topology affects which AFE pins drive balance (`CELL_1-N`)
        """),
    "wiki/concepts/soc-soh-sop.md": textwrap.dedent("""\
        # SOC, SOH, SOP Estimation

        | State | Meaning | Sensor basis |
        |-------|---------|--------------|
        | SOC | State of Charge 0–100% | Coulomb counting + OCV correction |
        | SOH | State of Health ~70% EOL | Capacity fade, impedance |
        | SOP | State of Power | Voltage + current limits under load |

        ## CANary (architecture phase)
        - MCU `telemetry.soc_pct` placeholder in architecture JSON
        - Requires `current_sensor` + `memory` for calibration
        - Simulation module (planned) will inject SOC trajectories
        """),
    "wiki/concepts/thermal-management.md": textwrap.dedent("""\
        # Thermal Management

        ## Operating band
        Typically 15–35 °C optimal; −20 to 60 °C operating for many Li-ion packs.

        ## BMS actions
        1. Fan/pump on (`cooling.fan = ON`)
        2. Derate current
        3. Open contactor (emergency)

        ## CANary rules (examples)
        ```yaml
        - id: thermal_fan_on
          condition: "pack_temp_c > 75"
          action: "cooling.fan = ON"
          component: mcu
        - id: thermal_shutdown
          condition: "pack_temp_c > 85"
          action: "contactor.main = OPEN"
          component: mcu
        ```

        Requires `temperature_network` node with NTC count matching series cells or zones.
        """),
    "wiki/concepts/topology-series-parallel.md": textwrap.dedent("""\
        # Pack Topology (Series / Parallel)

        ## Notation
        `12s2p` = 12 series × 2 parallel = 24 cells, 12s terminal voltage.

        ## CANary schematic rules (critical)
        - `pack.cell_count = series × parallel`
        - Widen `cells` node for series count
        - AFE `CELL_1-N` matches series; add 2nd AFE if >16s or >12s per LTC6811
        - 2p+ requires `busbars` node in pack view
        - Chemistry drives `nominal_voltage_v` and OVP/UVP in safety rules

        ## IC selection
        | Series | Suggested AFE |
        |--------|---------------|
        | ≤16 | BQ76952 |
        | >16 or isoSPI | LTC6811 (stacked) |
        """),
    "wiki/entities/bq76952.md": textwrap.dedent("""\
        # BQ76952 — TI Battery Monitor AFE

        > PDF: `raw/datasheets/bq76952.pdf` | Tags: afe, ti, ≤16s

        ## Summary
        Integrated AFE for 3–16 series Li-ion/LiFePO₄ with passive balancing, protection, I2C.

        ## Key specs
        | Parameter | Value |
        |-----------|-------|
        | Series cells | 3–16 |
        | Interface | I2C, HDQ |
        | Balancing | Integrated passive |
        | ADC | Cell voltage, pack current (via CC) |

        ## Schematic (CANary)
        - Node: `cell_monitor_ic`, `component_ref: cell_monitor_0`
        - Pins: `I2C`, `CELL_1-N`, `VDD`, `GND`
        - MCU connects via I2C to STM32F407 or ESP32-S3

        ## Default thresholds (verify against chemistry + PDF)
        | Chemistry | OVP | UVP |
        |-----------|-----|-----|
        | NMC | 4.25 V | 2.5 V |
        | LFP | 3.65 V | 2.5 V |

        ## Source
        - [wiki/sources/bq76952-datasheet.md](../sources/bq76952-datasheet.md)
        """),
    "wiki/entities/ltc6811.md": textwrap.dedent("""\
        # LTC6811 — ADI Multicell Monitor

        > PDF: pending upload to `raw/datasheets/ltc6811.pdf`

        ## Summary
        12-cell monitor, isoSPI daisy-chain for high-voltage EV/ESS packs.

        ## CANary
        - Use when user specifies LTC6811 or series >16
        - Two `cell_monitor_ic` nodes for 24s
        - Split pins CELL_1-8 / CELL_9-12 per IC
        """),
    "wiki/entities/stm32f407.md": textwrap.dedent("""\
        # STM32F407 — BMS MCU

        ## Role
        Protection logic, balancing control, CAN diagnostics, rule engine host.

        ## CANary
        - Node `mcu`, `component: mcu` in all safety rules
        - Pins: I2C to AFE, CAN to transceiver, GPIO to contactor driver
        """),
    "wiki/sources/bq76952-datasheet.md": textwrap.dedent("""\
        # Source: TI BQ76952 Datasheet

        > **PDF:** `raw/datasheets/bq76952.pdf` (uploaded to Tigris)
        > **Ingested:** {now}
        > **Tags:** datasheet, afe, ti

        ## Document scope
        Official TI datasheet for BQ76952 battery monitor — electrical specs, registers, balancing, protection.

        ## Extracted highlights (agent-compiled)
        - 3–16 cell support — fits ≤16s packs without second AFE
        - Integrated passive balancing per cell
        - I2C interface to host MCU
        - Protection: OV, UV, OC, OT, UT — thresholds programmable via registers

        ## CANary design impact
        | Topic | Action |
        |-------|--------|
        | Topology ≤16s | Single `cell_monitor_ic`, part BQ76952 |
        | Pin naming | `CELL_1-N` where N = series count |
        | Safety rules | OVP/UVP from chemistry table in [entities/bq76952.md](../entities/bq76952.md) |
        | Balancing | Include `balancing` node linked to AFE |

        ## Agent guidance
        Before proposing BQ76952 thresholds, read this page + entity page. For register-level detail, download PDF from Tigris raw/.
        """).format(now=NOW),
    "wiki/sources/ul-2580-overview.md": textwrap.dedent("""\
        # Source: UL 2580 (EV Battery Pack Safety) — Overview

        > **PDF:** `raw/standards/ul-2580.pdf` (placeholder — upload full standard)
        > **Tags:** standard, ul, ev

        ## Relevance to CANary
        OVP, UVP, thermal, isolation, abuse context for EV pack BMS rules.

        ## Agent guidance
        When user mentions UL 2580 or EV certification, cite conservative thresholds and note CANary does not replace formal UL testing.
        """),
}


def _manifest() -> dict:
    return {
        "version": "1.0",
        "knowledge_base": {
            "name": "canary-bms-default",
            "bucket": "canary-bms-knowledge",
            "prefix": "dev/default",
            "retriever_kb_id": None,
        },
        "documents": [
            {
                "id": "bq76952-datasheet",
                "title": "TI BQ76952 Datasheet",
                "type": "datasheet",
                "raw_pdf": "raw/datasheets/bq76952.pdf",
                "wiki_source": "wiki/sources/bq76952-datasheet.md",
                "wiki_entity": "wiki/entities/bq76952.md",
                "tags": ["afe", "ti", "bq76952"],
            },
            {
                "id": "ul-2580",
                "title": "UL 2580 Overview",
                "type": "standard",
                "raw_pdf": "raw/standards/ul-2580.pdf",
                "wiki_source": "wiki/sources/ul-2580-overview.md",
                "tags": ["standard", "ul", "ev"],
            },
        ],
    }


def _build_index() -> str:
    return textwrap.dedent(f"""\
        # CANary BMS Wiki Index

        > Remote wiki on Tigris — Karpathy LLM Wiki pattern
        > Last enriched: {NOW}

        ## Operations
        - [ingest-pipeline](ingest-pipeline.md) — PDF upload, extraction, wiki compile

        ## Scope
        - [project-scope](scope/project-scope.md)
        - [user-scope](scope/user-scope.md)

        ## Concepts
        - [protection-systems](concepts/protection-systems.md)
        - [cell-balancing](concepts/cell-balancing.md)
        - [soc-soh-sop](concepts/soc-soh-sop.md)
        - [thermal-management](concepts/thermal-management.md)
        - [topology-series-parallel](concepts/topology-series-parallel.md)

        ## Entities (parts)
        - [BQ76952](entities/bq76952.md)
        - [LTC6811](entities/ltc6811.md)
        - [STM32F407](entities/stm32f407.md)

        ## Sources (1:1 per PDF)
        - [bq76952-datasheet](sources/bq76952-datasheet.md)
        - [ul-2580-overview](sources/ul-2580-overview.md)

        ## Engineering
        - [coding-conventions](engineering/coding-conventions.md)
        - [repo-layout](engineering/repo-layout.md)

        ## Reference
        - [overview](overview.md)
        - [synthesis](synthesis.md)
        """)


def _append_log(settings, entry: str) -> None:
    existing = get_text(settings, "wiki/log.md") or "# Log\n"
    put_text(settings, "wiki/log.md", existing.rstrip() + f"\n\n{entry}\n")


def download_and_upload_pdfs(settings) -> list[str]:
    uploaded: list[str] = []
    for rel, (url, ctype) in PDF_SOURCES.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CANary-BMS/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            put_bytes(settings, rel, data, content_type=ctype)
            uploaded.append(rel)
        except Exception as exc:
            uploaded.append(f"{rel} (FAILED: {exc})")
    return uploaded


def enrich(*, skip_pdf: bool = False) -> dict:
    settings = get_tigris_settings()
    if not settings.configured:
        raise RuntimeError("Tigris not configured")

    results: dict = {"markdown": [], "pdfs": [], "manifest": None}

    put_text(settings, "wiki/index.md", _build_index())
    results["markdown"].append("wiki/index.md")

    for rel, content in ENRICH_MARKDOWN.items():
        put_text(settings, rel, content)
        results["markdown"].append(rel)

    manifest_yaml = yaml.safe_dump(_manifest(), sort_keys=False, allow_unicode=True)
    put_text(settings, "manifest.yaml", manifest_yaml, content_type="text/yaml")
    results["manifest"] = "manifest.yaml"

    _append_log(
        settings,
        f"## [{NOW.split()[0]}] enrich | Detailed BMS concepts, entities, sources, ingest pipeline",
    )

    if not skip_pdf:
        results["pdfs"] = download_and_upload_pdfs(settings)
        if any("bq76952.pdf" in p and "FAILED" not in p for p in results["pdfs"]):
            _append_log(settings, f"## [{NOW.split()[0]}] ingest | bq76952.pdf uploaded to raw/datasheets/")

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrich CANary BMS wiki on Tigris")
    parser.add_argument("--skip-pdf", action="store_true")
    parser.add_argument("--report", action="store_true", help="Print object counts after enrich")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[4]
    load_dotenv(repo_root / ".env")

    results = enrich(skip_pdf=args.skip_pdf)
    print("Enriched markdown:", len(results["markdown"]))
    for path in results["markdown"]:
        print(f"  {path}")
    print("PDFs:", results["pdfs"])
    print("Manifest:", results["manifest"])

    if args.report:
        settings = get_tigris_settings()
        keys = list_prefix(settings)
        print(f"\nTotal objects under prefix: {len(keys)}")
        for folder in ("wiki/concepts/", "wiki/entities/", "wiki/sources/", "raw/datasheets/"):
            count = len([k for k in keys if folder in k and not k.endswith(".keep")])
            print(f"  {folder}: {count} objects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
