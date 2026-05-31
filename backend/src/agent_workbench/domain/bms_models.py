"""Pydantic models for BMS architecture and safety rules."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SchematicPin(BaseModel):
    id: str
    label: str
    side: Literal["left", "right", "top", "bottom"]


class SchematicNode(BaseModel):
    id: str
    type: str
    label: str
    x: float
    y: float
    width: float = Field(ge=40)
    height: float = Field(ge=30)
    pins: list[SchematicPin] = Field(default_factory=list)
    drill_view: Literal["bms"] | None = None
    component_ref: str | None = None
    telemetry: dict[str, str | int | float] | None = None


class SchematicEdge(BaseModel):
    from_node: str
    from_pin: str
    to_node: str
    to_pin: str
    signal: str


class SchematicView(BaseModel):
    nodes: list[SchematicNode] = Field(min_length=1)
    edges: list[SchematicEdge] = Field(default_factory=list)


class PackInfo(BaseModel):
    topology: str
    cell_count: int = Field(ge=1)
    chemistry: str
    nominal_voltage_v: float = Field(ge=0)


class BmsViews(BaseModel):
    pack: SchematicView
    bms: SchematicView


class BmsArchitecture(BaseModel):
    schema_version: Literal["1.0"]
    pack: PackInfo
    views: BmsViews
    components: dict[str, Any] = Field(default_factory=dict)

    @field_validator("views")
    @classmethod
    def validate_edges(cls, views: BmsViews) -> BmsViews:
        for view_name, view in [("pack", views.pack), ("bms", views.bms)]:
            node_ids = {n.id for n in view.nodes}
            pin_map: dict[str, set[str]] = {}
            for node in view.nodes:
                pin_map[node.id] = {p.id for p in node.pins}
            for edge in view.edges:
                if edge.from_node not in node_ids:
                    raise ValueError(f"views.{view_name}: edge references unknown from_node '{edge.from_node}'")
                if edge.to_node not in node_ids:
                    raise ValueError(f"views.{view_name}: edge references unknown to_node '{edge.to_node}'")
                if edge.from_pin not in pin_map.get(edge.from_node, set()):
                    raise ValueError(
                        f"views.{view_name}: edge from '{edge.from_node}' references unknown pin '{edge.from_pin}'"
                    )
                if edge.to_pin not in pin_map.get(edge.to_node, set()):
                    raise ValueError(
                        f"views.{view_name}: edge to '{edge.to_node}' references unknown pin '{edge.to_pin}'"
                    )
        return views


class SafetyRule(BaseModel):
    id: str
    condition: str
    action: str
    component: str | None = None
    description: str | None = None


class SafetyRulesDocument(BaseModel):
    rules: list[SafetyRule]

    @classmethod
    def from_list(cls, data: list[dict[str, Any]]) -> SafetyRulesDocument:
        return cls(rules=[SafetyRule.model_validate(item) for item in data])
