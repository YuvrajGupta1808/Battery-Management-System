"""Tests for pack-driven schematic reshaping."""

import json
from pathlib import Path

from agent_workbench.services.topology_layout import reshape_architecture_for_topology

FIXTURES = Path(__file__).parent / "fixtures" / "bms"


def test_reshape_widens_cells_for_12s() -> None:
    data = json.loads((FIXTURES / "architecture.bms.json").read_text(encoding="utf-8"))
    data["pack"]["topology"] = "12s1p"
    data["pack"]["cell_count"] = 12

    reshaped = reshape_architecture_for_topology(data)
    cells = next(n for n in reshaped["views"]["pack"]["nodes"] if n["type"] == "cells")

    assert cells["width"] > 200
    assert "12S" in cells["label"]


def test_reshape_syncs_afe_pins() -> None:
    data = json.loads((FIXTURES / "architecture.bms.json").read_text(encoding="utf-8"))
    data["pack"]["topology"] = "12s2p"
    data["pack"]["cell_count"] = 24

    reshaped = reshape_architecture_for_topology(data)
    afe = next(n for n in reshaped["views"]["bms"]["nodes"] if n["type"] == "cell_monitor_ic")
    cell_pin = next(p for p in afe["pins"] if str(p["label"]).startswith("CELL_"))

    assert cell_pin["label"] == "CELL_1-12"
    assert afe["telemetry"]["cells_monitored"] == 12


def test_reshape_injects_second_afe_over_16s() -> None:
    data = json.loads((FIXTURES / "architecture.bms.json").read_text(encoding="utf-8"))
    data["pack"]["topology"] = "24s1p"
    data["pack"]["cell_count"] = 24

    reshaped = reshape_architecture_for_topology(data)
    ids = [n["id"] for n in reshaped["views"]["bms"]["nodes"]]

    assert "cell_ic_2" in ids
