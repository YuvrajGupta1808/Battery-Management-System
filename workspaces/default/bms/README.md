# BMS Diagram Artifacts

CANary stores BMS circuit diagrams as structured workspace files. **The coding agent authors these files**; the UI renders them as SVG schematics.

## Files the agent creates

| Path | Purpose |
|------|---------|
| `bms/architecture.bms.json` | Pack topology, schematic views, component metadata |
| `bms/safety_rules.yaml` | Protection rules (thermal, voltage, current) |
| `bms/components/*.json` | Optional per-component detail |

## Authoring reference

- Schema: `bms/schema/architecture.schema.json`
- **Reference template** (copy, then customize): `bms/templates/architecture.template.bms.json` — full 4s1p pack + BMS schematic with `template_meta` describing what to change
- **Safety rules template**: `bms/templates/safety_rules.template.yaml`
- Agent skill: `bms/SKILL.md`

## Views

- **`views.pack`** — Top-level pack diagram (cells, busbars, cooling, BMS board, contactor)
- **`views.bms`** — BMS internals (MCU, cell monitor ICs, temp network, balancing, current sensor, CAN, memory)

Set `drill_view: "bms"` on the pack-level BMS node so the UI drill-down works.
