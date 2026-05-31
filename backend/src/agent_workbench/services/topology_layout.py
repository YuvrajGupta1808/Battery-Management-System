"""Reshape BMS schematic layout from pack topology (mirrors frontend topologyLayout.ts)."""

from __future__ import annotations

import copy
import re
from typing import Any

TOPOLOGY_RE = re.compile(r"^(\d+)s(\d+)p$", re.IGNORECASE)
CELL_PIN_RE = re.compile(r"^CELL_", re.IGNORECASE)
NTC_PIN_RE = re.compile(r"^NTC_", re.IGNORECASE)


def _parse_topology(topology: str) -> tuple[int, int] | None:
    match = TOPOLOGY_RE.match(topology.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _cell_stack_dimensions(series: int, parallel: int) -> tuple[int, int]:
    width = min(720, max(140, 48 + series * 22))
    height = max(72, 56 + max(0, parallel - 1) * 36)
    return width, height


def _afe_dimensions(series: int) -> tuple[int, int]:
    width = min(300, max(170, 100 + series * 7))
    height = max(95, 80 + (series // 4) * 10)
    return width, height


def _series_cell_pin_label(series: int) -> str:
    return "CELL_1" if series <= 1 else f"CELL_1-{series}"


def _stack_label(series: int, parallel: int, chemistry: str) -> str:
    topo = f"{series}S{parallel}P" if parallel > 1 else f"{series}S"
    return f"{topo} {chemistry} Stack"


def _find_by_type(nodes: list[dict[str, Any]], node_type: str) -> dict[str, Any] | None:
    for node in nodes:
        if node.get("type") == node_type:
            return node
    return None


def _update_pin_label(node: dict[str, Any], pattern: re.Pattern[str], label: str) -> None:
    for pin in node.get("pins") or []:
        if isinstance(pin, dict) and pattern.search(str(pin.get("label", ""))):
            pin["label"] = label


def _shift_nodes_right(nodes: list[dict[str, Any]], from_x: float, delta_x: float) -> None:
    if delta_x <= 0:
        return
    for node in nodes:
        if float(node.get("x", 0)) >= from_x:
            node["x"] = float(node.get("x", 0)) + delta_x


def _enrich_node_label(node: dict[str, Any], components: dict[str, Any]) -> None:
    ref = node.get("component_ref")
    if not ref or ref not in components:
        return
    part = components[ref].get("part")
    if not isinstance(part, str) or not part.strip():
        return
    label = str(node.get("label", ""))
    if re.search(r"\s[–—-]\s", label):
        return
    node_type = str(node.get("type", ""))
    if node_type in {"cells", "bms_board", "contactor"}:
        return
    roles = {
        "mcu": "MCU",
        "cell_monitor_ic": "Cell Monitor AFE",
        "can_transceiver": "CAN Transceiver",
        "temperature_network": "Temp Network",
        "balancing": "Cell Balancing",
        "current_sensor": "Current Monitor",
        "memory": "EEPROM / Flash",
    }
    role = roles.get(node_type, node_type.replace("_", " "))
    node["label"] = f"{role} – {part}"


def _resolve_part_label(node: dict[str, Any], components: dict[str, Any]) -> None:
    _enrich_node_label(node, components)


def _adapt_pack_view(view: dict[str, Any], pack: dict[str, Any], series: int, parallel: int) -> None:
    nodes = view.get("nodes") or []
    cells = _find_by_type(nodes, "cells")
    if not cells:
        return

    prev_width = float(cells.get("width", 200))
    width, height = _cell_stack_dimensions(series, parallel)
    cells["width"] = width
    cells["height"] = height
    cells["label"] = _stack_label(series, parallel, str(pack.get("chemistry", "")))
    cells["y"] = max(280, 460 - height)

    width_delta = width - prev_width
    if width_delta > 0:
        _shift_nodes_right(nodes, float(cells.get("x", 0)) + prev_width + 20, width_delta)

    bms_board = _find_by_type(nodes, "bms_board")
    if bms_board:
        min_gap = 44
        bms_board["x"] = max(float(bms_board.get("x", 0)), float(cells.get("x", 0)) + width + min_gap)

    contactor = _find_by_type(nodes, "contactor")
    if contactor and bms_board:
        contactor["x"] = max(
            float(contactor.get("x", 0)),
            float(bms_board.get("x", 0)) + float(bms_board.get("width", 0)) + 36,
        )


def _inject_second_afe(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    primary: dict[str, Any],
    series: int,
    part: str | None,
) -> None:
    if series <= 16 or any(n.get("id") == "cell_ic_2" for n in nodes):
        return

    second_series = series - 16
    start_cell = 17
    end_cell = start_cell + second_series - 1
    cell_label = f"CELL_{start_cell}" if second_series <= 1 else f"CELL_{start_cell}-{end_cell}"
    afe_w, afe_h = _afe_dimensions(second_series)

    nodes.append(
        {
            "id": "cell_ic_2",
            "type": "cell_monitor_ic",
            "label": f"{part} AFE (B)" if part else "Cell Monitor IC (B)",
            "x": primary.get("x", 60),
            "y": float(primary.get("y", 200)) + float(primary.get("height", 85)) + 36,
            "width": afe_w,
            "height": afe_h,
            "component_ref": f"{primary.get('component_ref')}_b" if primary.get("component_ref") else None,
            "telemetry": {"cells_monitored": second_series},
            "pins": [
                {"id": "cell_sense", "label": cell_label, "side": "left"},
                {"id": "i2c_sda", "label": "I2C_SDA", "side": "top"},
                {"id": "i2c_scl", "label": "I2C_SCL", "side": "top"},
                {"id": "bal_out", "label": "BAL_OUT", "side": "right"},
            ],
        }
    )

    mcu = _find_by_type(nodes, "mcu")
    if mcu:
        edges.append(
            {
                "from_node": mcu.get("id", "mcu"),
                "from_pin": "i2c_sda",
                "to_node": "cell_ic_2",
                "to_pin": "i2c_sda",
                "signal": "I2C_SDA",
            }
        )
        edges.append(
            {
                "from_node": mcu.get("id", "mcu"),
                "from_pin": "i2c_scl",
                "to_node": "cell_ic_2",
                "to_pin": "i2c_scl",
                "signal": "I2C_SCL",
            }
        )


def _adapt_bms_view(view: dict[str, Any], pack: dict[str, Any], series: int, components: dict[str, Any]) -> None:
    nodes = view.get("nodes") or []
    edges = view.get("edges") or []
    cell_label = _series_cell_pin_label(series)
    ntc_label = "NTC_1" if series <= 1 else f"NTC_1-{series}"

    cell_ic = _find_by_type(nodes, "cell_monitor_ic")
    if cell_ic:
        primary_series = 16 if series > 16 else series
        afe_w, afe_h = _afe_dimensions(primary_series)
        cell_ic["width"] = afe_w
        cell_ic["height"] = afe_h
        _update_pin_label(cell_ic, CELL_PIN_RE, _series_cell_pin_label(primary_series))
        telemetry = dict(cell_ic.get("telemetry") or {})
        telemetry["cells_monitored"] = primary_series
        cell_ic["telemetry"] = telemetry
        _resolve_part_label(cell_ic, components)

        part = None
        ref = cell_ic.get("component_ref")
        if ref and ref in components:
            raw = components[ref].get("part")
            part = raw if isinstance(raw, str) else None
            components[ref]["cells_monitored"] = primary_series if series > 16 else series
        if series > 16:
            _inject_second_afe(nodes, edges, cell_ic, series, part)
        elif ref and ref in components:
            components[ref]["cells_monitored"] = series

    temp_net = _find_by_type(nodes, "temperature_network")
    if temp_net:
        _update_pin_label(temp_net, NTC_PIN_RE, ntc_label)
        if cell_ic:
            temp_net["y"] = max(float(temp_net.get("y", 0)), float(cell_ic.get("y", 0)) + float(cell_ic.get("height", 0)) + 28)
        temp_telemetry = dict(temp_net.get("telemetry") or {})
        temp_telemetry["sensor_count"] = series
        temp_net["telemetry"] = temp_telemetry
        if "temp_network" in components:
            components["temp_network"]["sensor_count"] = series

    balancing = _find_by_type(nodes, "balancing")
    if balancing and cell_ic:
        balancing["y"] = max(float(balancing.get("y", 0)), float(cell_ic.get("y", 0)) + float(cell_ic.get("height", 0)) + 20)

    current = _find_by_type(nodes, "current_sensor")
    memory = _find_by_type(nodes, "memory")
    if current and memory:
        bottom_y = max(float(current.get("y", 0)), float(memory.get("y", 0)), 320)
        current["y"] = bottom_y
        memory["y"] = bottom_y + float(current.get("height", 70)) + 24
        if float(memory.get("x", 0)) <= float(current.get("x", 0)) + float(current.get("width", 0)):
            memory["x"] = float(current.get("x", 0)) + float(current.get("width", 140)) + 40

    for node in nodes:
        _resolve_part_label(node, components)


def reshape_architecture_for_topology(data: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy with pack-driven layout applied."""
    result = copy.deepcopy(data)
    pack = result.get("pack") or {}
    topology = str(pack.get("topology", ""))
    parsed = _parse_topology(topology)
    if not parsed:
        return result

    series, parallel = parsed
    views = result.setdefault("views", {})
    if "pack" in views:
        _adapt_pack_view(views["pack"], pack, series, parallel)
    if "bms" in views:
        components = result.setdefault("components", {})
        _adapt_bms_view(views["bms"], pack, series, components)

    return result
