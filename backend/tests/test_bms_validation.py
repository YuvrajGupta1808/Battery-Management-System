import json
from pathlib import Path

import pytest

from agent_workbench.domain.bms_models import BmsArchitecture, SafetyRulesDocument
from agent_workbench.services.bms_validation import validate_bms_file


FIXTURES = Path(__file__).parent / "fixtures" / "bms"


def test_valid_architecture_fixture() -> None:
    content = (FIXTURES / "architecture.bms.json").read_text(encoding="utf-8")
    validate_bms_file("bms/architecture.bms.json", content)
    arch = BmsArchitecture.model_validate(json.loads(content))
    assert arch.pack.topology == "4s1p"
    assert len(arch.views.pack.nodes) >= 3
    assert any(n.drill_view == "bms" for n in arch.views.pack.nodes)


def test_invalid_architecture_missing_view() -> None:
    bad = {
        "schema_version": "1.0",
        "pack": {"topology": "4s1p", "cell_count": 4, "chemistry": "NMC", "nominal_voltage_v": 14.8},
        "views": {
            "pack": {"nodes": [{"id": "a", "type": "x", "label": "A", "x": 0, "y": 0, "width": 80, "height": 60}], "edges": []},
            "bms": {"nodes": [{"id": "b", "type": "x", "label": "B", "x": 0, "y": 0, "width": 80, "height": 60}], "edges": [
                {"from_node": "b", "from_pin": "missing", "to_node": "b", "to_pin": "missing", "signal": "X"}
            ]},
        },
    }
    with pytest.raises(ValueError, match="unknown pin"):
        validate_bms_file("bms/architecture.bms.json", json.dumps(bad))


def test_valid_safety_rules() -> None:
    content = """\
- id: thermal_fan_on
  condition: "pack_temp_c > 80"
  action: "cooling.fan = ON"
  component: mcu
  description: Enable fan above 80C
"""
    validate_bms_file("bms/safety_rules.yaml", content)
    rules = SafetyRulesDocument.from_list([
        {"id": "thermal_fan_on", "condition": "pack_temp_c > 80", "action": "cooling.fan = ON", "component": "mcu"}
    ])
    assert rules.rules[0].id == "thermal_fan_on"


def test_invalid_safety_rules_missing_fields() -> None:
    content = "- id: only_id\n"
    with pytest.raises(ValueError, match="safety_rules.yaml"):
        validate_bms_file("bms/safety_rules.yaml", content)


def test_topology_cell_count_mismatch() -> None:
    content = (FIXTURES / "architecture.bms.json").read_text(encoding="utf-8")
    data = json.loads(content)
    data["pack"]["topology"] = "12s2p"
    data["pack"]["cell_count"] = 4
    with pytest.raises(ValueError, match="pack.cell_count"):
        validate_bms_file("bms/architecture.bms.json", json.dumps(data))


def test_topology_cell_pin_mismatch() -> None:
    content = (FIXTURES / "architecture.bms.json").read_text(encoding="utf-8")
    data = json.loads(content)
    data["pack"]["topology"] = "12s1p"
    data["pack"]["cell_count"] = 12
    for node in data["views"]["bms"]["nodes"]:
        if node.get("type") == "cell_monitor_ic":
            for pin in node.get("pins", []):
                if str(pin.get("label", "")).startswith("CELL_"):
                    pin["label"] = "CELL_1-4"
    with pytest.raises(ValueError, match="CELL_1-4"):
        validate_bms_file("bms/architecture.bms.json", json.dumps(data))
