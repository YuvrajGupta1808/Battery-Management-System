"""Validate BMS workspace files on read/write."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from ..domain.bms_models import BmsArchitecture, SafetyRulesDocument

BMS_ARCHITECTURE_RE = re.compile(r"(^|/)bms/.*\.bms\.json$", re.IGNORECASE)
BMS_SAFETY_RULES_RE = re.compile(r"(^|/)bms/safety_rules\.ya?ml$", re.IGNORECASE)
TOPOLOGY_RE = re.compile(r"^(\d+)s(\d+)p$", re.IGNORECASE)
CELL_PIN_RE = re.compile(r"CELL_1(?:-(\d+))?", re.IGNORECASE)


def is_bms_architecture_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    return bool(BMS_ARCHITECTURE_RE.search(normalized))


def is_bms_safety_rules_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    return bool(BMS_SAFETY_RULES_RE.search(normalized))


def validate_bms_file(path: str, content: str) -> None:
    """Raise ValueError with actionable message if content is invalid."""
    if is_bms_architecture_path(path):
        _validate_architecture(content)
        return
    if is_bms_safety_rules_path(path):
        _validate_safety_rules(content)
        return


def _validate_architecture(content: str) -> None:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in BMS architecture file: {exc.msg} at line {exc.lineno}") from exc
    try:
        BmsArchitecture.model_validate(data)
    except ValidationError as exc:
        raise ValueError(_format_validation_errors("BMS architecture", exc)) from exc
    _validate_topology_consistency(data)


def _validate_safety_rules(content: str) -> None:
    stripped = content.strip()
    if not stripped:
        raise ValueError("safety_rules.yaml must contain at least one safety rule")
    data = _parse_simple_yaml_list(content)
    if data is None:
        raise ValueError("safety_rules.yaml must be a YAML list of rules (- id: ... condition: ... action: ...)")
    if not data:
        raise ValueError("safety_rules.yaml must contain at least one complete safety rule")
    try:
        SafetyRulesDocument.from_list(data)
    except ValidationError as exc:
        raise ValueError(_format_validation_errors("Safety rules", exc)) from exc


def _format_validation_errors(label: str, exc: ValidationError) -> str:
    parts = [f"{label} validation failed:"]
    for err in exc.errors():
        loc = ".".join(str(x) for x in err["loc"])
        parts.append(f"  - {loc}: {err['msg']}")
    return "\n".join(parts)


def _unwrap_rules_key(content: str) -> str:
    """Accept `rules:\\n  - id:` wrappers agents often emit."""
    lines = content.splitlines()
    out: list[str] = []
    in_rules = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            out.append(line)
            continue
        if stripped == "rules:" or stripped.startswith("rules:"):
            in_rules = True
            continue
        if in_rules and line.startswith("  "):
            out.append(line[2:])
            continue
        in_rules = False
        out.append(line)
    return "\n".join(out)


def _parse_simple_yaml_list(content: str) -> list[dict[str, Any]] | None:
    """Parse a YAML list of mapping items without external deps."""
    content = _unwrap_rules_key(content)
    lines = content.splitlines()
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    saw_list = False

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            saw_list = True
            if current is not None:
                if not _is_complete_rule(current):
                    return None
                items.append(current)
            current = {}
            rest = stripped[2:].strip()
            if rest and ":" in rest:
                key, _, val = rest.partition(":")
                current[key.strip()] = _yaml_scalar(val.strip())
            continue
        if current is not None and ":" in stripped:
            key, _, val = stripped.partition(":")
            current[key.strip()] = _yaml_scalar(val.strip())
            continue
        return None

    if current is not None:
        if not _is_complete_rule(current):
            return None
        items.append(current)

    if not saw_list and content.strip():
        return None
    return items


def _is_complete_rule(item: dict[str, Any]) -> bool:
    return bool(item.get("id") and item.get("condition") and item.get("action"))


def _yaml_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _validate_topology_consistency(data: dict[str, Any]) -> None:
    """Ensure pack metadata matches schematic pin labels agents usually set."""
    pack = data.get("pack") or {}
    topology = str(pack.get("topology", "")).strip()
    match = TOPOLOGY_RE.match(topology)
    if not match:
        return

    series = int(match.group(1))
    parallel = int(match.group(2))
    expected_cells = series * parallel
    cell_count = pack.get("cell_count")
    if isinstance(cell_count, int) and cell_count != expected_cells:
        raise ValueError(
            f"BMS architecture validation failed:\n"
            f"  - pack.cell_count: expected {expected_cells} for topology {topology} "
            f"({series} series × {parallel} parallel), got {cell_count}"
        )

    bms_nodes = ((data.get("views") or {}).get("bms") or {}).get("nodes") or []
    for node in bms_nodes:
        if not isinstance(node, dict) or node.get("type") != "cell_monitor_ic":
            continue
        for pin in node.get("pins") or []:
            if not isinstance(pin, dict):
                continue
            label = str(pin.get("label", ""))
            pin_match = CELL_PIN_RE.search(label)
            if not pin_match:
                continue
            pin_series = int(pin_match.group(1) or "1")
            if pin_series != series:
                raise ValueError(
                    f"BMS architecture validation failed:\n"
                    f"  - views.bms node '{node.get('id')}': pin '{label}' implies {pin_series}S "
                    f"but pack.topology is {topology} ({series}S)"
                )
            break
