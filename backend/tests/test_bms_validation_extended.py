"""Extended BMS validation and path detection tests."""

import json
from pathlib import Path

import pytest

from agent_workbench.domain.bms_models import BmsArchitecture, SchematicNode
from agent_workbench.services.bms_validation import (
    is_bms_architecture_path,
    is_bms_safety_rules_path,
    validate_bms_file,
)

FIXTURES = Path(__file__).parent / "fixtures" / "bms"
WORKSPACE_BMS = Path(__file__).resolve().parents[2] / "workspaces" / "default" / "bms"


def _minimal_arch(**overrides: object) -> dict:
    base = {
        "schema_version": "1.0",
        "pack": {"topology": "4s1p", "cell_count": 4, "chemistry": "NMC", "nominal_voltage_v": 14.8},
        "views": {
            "pack": {
                "nodes": [
                    {
                        "id": "n1",
                        "type": "bms_board",
                        "label": "BMS",
                        "x": 10,
                        "y": 10,
                        "width": 80,
                        "height": 60,
                        "drill_view": "bms",
                        "pins": [{"id": "p1", "label": "A", "side": "left"}],
                    }
                ],
                "edges": [],
            },
            "bms": {
                "nodes": [
                    {
                        "id": "mcu",
                        "type": "mcu",
                        "label": "MCU",
                        "x": 20,
                        "y": 20,
                        "width": 100,
                        "height": 70,
                        "pins": [],
                    }
                ],
                "edges": [],
            },
        },
    }
    if overrides:
        base.update(overrides)
    return base


@pytest.mark.parametrize(
    "path,expected",
    [
        ("bms/architecture.bms.json", True),
        ("/bms/architecture.bms.json", True),
        ("bms/custom-pack.bms.json", True),
        ("BMS/Architecture.BMS.JSON", True),
        ("bms/safety_rules.yaml", False),
        ("architecture.bms.json", False),
        ("bms/architecture.json", False),
        ("README.md", False),
    ],
)
def test_is_bms_architecture_path(path: str, expected: bool) -> None:
    assert is_bms_architecture_path(path) is expected


@pytest.mark.parametrize(
    "path,expected",
    [
        ("bms/safety_rules.yaml", True),
        ("bms/safety_rules.yml", True),
        ("/bms/safety_rules.yaml", True),
        ("bms/architecture.bms.json", False),
        ("safety_rules.yaml", False),
    ],
)
def test_is_bms_safety_rules_path(path: str, expected: bool) -> None:
    assert is_bms_safety_rules_path(path) is expected


def test_validate_bms_file_skips_non_bms_paths() -> None:
    validate_bms_file("README.md", "not json")
    validate_bms_file("src/main.py", "print('hi')")


def test_invalid_json_architecture() -> None:
    with pytest.raises(ValueError, match="Invalid JSON"):
        validate_bms_file("bms/architecture.bms.json", "{broken")


def test_missing_schema_version() -> None:
    data = _minimal_arch()
    del data["schema_version"]
    with pytest.raises(ValueError, match="schema_version"):
        validate_bms_file("bms/architecture.bms.json", json.dumps(data))


def test_wrong_schema_version() -> None:
    data = _minimal_arch()
    data["schema_version"] = "2.0"
    with pytest.raises(ValueError, match="schema_version"):
        validate_bms_file("bms/architecture.bms.json", json.dumps(data))


def test_invalid_cell_count() -> None:
    data = _minimal_arch()
    data["pack"]["cell_count"] = 0
    with pytest.raises(ValueError, match="cell_count"):
        validate_bms_file("bms/architecture.bms.json", json.dumps(data))


def test_unknown_from_node_in_edge() -> None:
    data = _minimal_arch()
    data["views"]["pack"]["edges"] = [
        {"from_node": "ghost", "from_pin": "p1", "to_node": "n1", "to_pin": "p1", "signal": "X"}
    ]
    with pytest.raises(ValueError, match="unknown from_node"):
        validate_bms_file("bms/architecture.bms.json", json.dumps(data))


def test_unknown_to_node_in_edge() -> None:
    data = _minimal_arch()
    data["views"]["bms"]["edges"] = [
        {"from_node": "mcu", "from_pin": "p1", "to_node": "ghost", "to_pin": "p1", "signal": "X"}
    ]
    data["views"]["bms"]["nodes"][0]["pins"] = [{"id": "p1", "label": "P", "side": "right"}]
    with pytest.raises(ValueError, match="unknown to_node"):
        validate_bms_file("bms/architecture.bms.json", json.dumps(data))


def test_node_too_small_dimensions() -> None:
    data = _minimal_arch()
    data["views"]["pack"]["nodes"][0]["width"] = 10
    with pytest.raises(ValueError, match="width"):
        validate_bms_file("bms/architecture.bms.json", json.dumps(data))


def test_empty_pack_nodes_rejected() -> None:
    data = _minimal_arch()
    data["views"]["pack"]["nodes"] = []
    with pytest.raises(ValueError):
        validate_bms_file("bms/architecture.bms.json", json.dumps(data))


def test_valid_edge_between_pinned_nodes() -> None:
    data = _minimal_arch()
    data["views"]["bms"]["nodes"] = [
        {
            "id": "mcu",
            "type": "mcu",
            "label": "MCU",
            "x": 0,
            "y": 0,
            "width": 80,
            "height": 60,
            "pins": [{"id": "out", "label": "OUT", "side": "right"}],
        },
        {
            "id": "can",
            "type": "can_transceiver",
            "label": "CAN",
            "x": 200,
            "y": 0,
            "width": 80,
            "height": 60,
            "pins": [{"id": "in", "label": "IN", "side": "left"}],
        },
    ]
    data["views"]["bms"]["edges"] = [
        {"from_node": "mcu", "from_pin": "out", "to_node": "can", "to_pin": "in", "signal": "CAN_TX"}
    ]
    validate_bms_file("bms/architecture.bms.json", json.dumps(data))


def test_fixture_has_all_bms_component_types() -> None:
    content = (FIXTURES / "architecture.bms.json").read_text(encoding="utf-8")
    arch = BmsArchitecture.model_validate(json.loads(content))
    types = {n.type for n in arch.views.bms.nodes}
    expected = {
        "mcu",
        "cell_monitor_ic",
        "temperature_network",
        "current_sensor",
        "balancing",
        "can_transceiver",
        "memory",
    }
    assert expected.issubset(types)


def test_fixture_components_metadata() -> None:
    content = (FIXTURES / "architecture.bms.json").read_text(encoding="utf-8")
    arch = BmsArchitecture.model_validate(json.loads(content))
    assert arch.components["mcu"]["part"] == "STM32F407"
    assert arch.components["cell_monitor_0"]["part"] == "BQ76952"


def test_safety_rules_multiple_entries() -> None:
    content = """\
- id: rule_a
  condition: "a > 1"
  action: "do_a()"
  component: mcu
- id: rule_b
  condition: "b > 2"
  action: "do_b()"
  component: memory
"""
    validate_bms_file("bms/safety_rules.yaml", content)


def test_safety_rules_empty_file_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        validate_bms_file("bms/safety_rules.yaml", "   \n  ")


def test_safety_rules_comments_ignored() -> None:
    content = """\
# thermal protection
- id: fan_on
  condition: "temp > 75"
  action: "fan.on()"
"""
    validate_bms_file("bms/safety_rules.yaml", content)


def test_safety_rules_rules_wrapper_accepted() -> None:
    content = """\
# BMS Safety Rules
rules:
  - id: RULE_FAN_ON
    condition: "pack_temp_c > 75.0"
    action: "enable_fan"
    component: mcu
    description: Fan on above 75C
"""
    validate_bms_file("bms/safety_rules.yaml", content)


def test_safety_rules_quoted_scalars() -> None:
    content = """\
- id: ovp
  condition: '"voltage > 4.25"'
  action: "fault(OVP)"
"""
    validate_bms_file("bms/safety_rules.yaml", content)


def test_workspace_schema_files_exist() -> None:
    assert (WORKSPACE_BMS / "SKILL.md").is_file()
    assert (WORKSPACE_BMS / "schema" / "architecture.schema.json").is_file()
    assert (WORKSPACE_BMS / "templates" / "architecture.template.bms.json").is_file()
    assert (WORKSPACE_BMS / "templates" / "safety_rules.template.yaml").is_file()
    template = json.loads((WORKSPACE_BMS / "templates" / "architecture.template.bms.json").read_text())
    assert template["schema_version"] == "1.0"
    assert "template_meta" in template
    assert template["template_meta"]["output_file"] == "bms/architecture.bms.json"
    assert len(template["views"]["pack"]["nodes"]) >= 3
    assert len(template["views"]["bms"]["nodes"]) >= 5
    validate_bms_file("bms/architecture.bms.json", json.dumps({k: v for k, v in template.items() if k != "template_meta"}))
    skill = (WORKSPACE_BMS / "SKILL.md").read_text(encoding="utf-8")
    assert "architecture.bms.json" in skill
    assert "templates/architecture.template" in skill


def test_schematic_node_drill_view_literal() -> None:
    node = SchematicNode(
        id="b",
        type="bms_board",
        label="BMS",
        x=0,
        y=0,
        width=80,
        height=60,
        drill_view="bms",
    )
    assert node.drill_view == "bms"
