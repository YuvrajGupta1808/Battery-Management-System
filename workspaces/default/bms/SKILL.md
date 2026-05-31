---
name: bms-diagram-author
description: Author BMS circuit diagrams as architecture.bms.json and safety_rules.yaml for CANary SVG rendering.
---

# BMS Diagram Authoring

You create and maintain BMS circuit diagrams by writing structured files into the workspace. The UI renders `bms/architecture.bms.json` as an interactive SVG schematic — you are the author, not the user.

**Users only describe requirements** (topology, chemistry, parts, thresholds). They do **not** need to say "read templates", "write both files", or "stop". That workflow is defined here and in your system prompt — follow it every time.

## Agent behavior (automatic on every new design request)

1. Read this file, `bms/templates/architecture.template.bms.json`, and `bms/templates/safety_rules.template.yaml` **once**
2. `write_file` full content to `bms/architecture.bms.json` and `bms/safety_rules.yaml` in one batch (overwrite OK)
3. Customize from the user's request: pack fields, part numbers in `components`, node labels, thresholds in rules
4. **Topology-specific schematic changes** — see [Topology customization (required)](#topology-customization-required); do not only edit `pack{}` metadata
5. Short summary to the user — **stop** (no todos, no post-write verification reads, no schema unless write fails)

**Do not edit files under `bms/templates/`** — read-only references.

The architecture template includes `template_meta.generation_checklist` and a **complete 4s1p example** (pack + BMS views with all required node types). Start from the template file, not empty `nodes: []` and not the minimal inline example below.

**Auto-layout on save:** when you write `architecture.bms.json`, the workbench **reshapes node sizes and positions from `pack.topology`** (cell stack width, AFE block size, pin labels, part labels). You still must set correct `pack` fields and part numbers — do not assume a 4s1p skeleton stays valid for 12s2p without updating chemistry, voltage, and safety thresholds.

## File tools (important)

| Situation | Tool |
|-----------|------|
| Create or replace `bms/architecture.bms.json` | `write_file` with full JSON (overwrite OK in this workbench) |
| Create or replace `bms/safety_rules.yaml` | `write_file` with full YAML list (overwrite OK) |
| Small threshold tweak on existing rules | `edit_file` on the changed lines only |
| Write rejected with validation error | Read the error, fix dangling edges or missing pins, `write_file` again |

**After a successful `write_file`:** do not re-read the file to verify — backend validation already ran. A default `read_file` only shows **100 lines**; `architecture.bms.json` is ~400 lines and will look truncated unless you pass `limit=500`.

**Paths:** use workspace paths (`/bms/architecture.bms.json`). Never typo host paths like `/Users/users/...`.

**Edge rule:** every `edges[]` entry must use `from_node` / `to_node` ids that exist in that view's `nodes[]`, and `from_pin` / `to_pin` ids that exist on those nodes. Do not reference `cell_1`, `contactor_ctrl`, or other nodes that are not declared.

**Safety rules format:** top-level YAML **list** — do **not** wrap rules in a `rules:` key:

```yaml
- id: thermal_fan_on
  condition: "pack_temp_c > 75"
  action: "cooling.fan = ON"
  component: mcu
```

Use `component: mcu` (BMS view node id) so the inspector links rules to the MCU block.

## Output files

| File | When to write |
|------|---------------|
| `bms/architecture.bms.json` | New pack design, topology change, component swap, layout update |
| `bms/safety_rules.yaml` | New BMS, threshold change, new protection rule |
| `bms/components/<id>.json` | Optional extended metadata for a component |

## architecture.bms.json rules

- `schema_version` must be `"1.0"`
- `pack`: topology (e.g. `12s2p`), cell_count, chemistry (`NMC`, `LFP`), nominal_voltage_v
- `views.pack`: top-level schematic — include cells, busbars, cooling, **bms_board** (with `drill_view: "bms"`), contactor
- `views.bms`: BMS internals — mcu, cell_monitor_ic(s), temperature_network, balancing, current_sensor, can_transceiver, memory
- Every node needs explicit `x`, `y`, `width`, `height` (coordinates in schematic units, ~800×600 canvas)
- Every functional block needs `pins[]` with `id`, `label`, `side` (`left`|`right`|`top`|`bottom`)
- `edges[]` connect pins: `from_node`, `from_pin`, `to_node`, `to_pin`, `signal`
- `components` object holds part numbers and telemetry placeholders agents can update

### IC selection heuristics

| Requirement | Suggested parts |
|-------------|-----------------|
| ≤16 cells, integrated AFE | BQ76952 |
| High cell count, isoSPI | LTC6811 |
| MCU | STM32F407, ESP32-S3, NXP S32K144 |
| Current sense | INA226 + shunt |
| CAN | MCP2551, TJA1051 |

### Layout conventions

- Pack view: cells bottom, BMS center-right, contactor right, cooling top
- BMS view: MCU center-top; cell monitor ICs left; CAN + memory right; current sensor bottom
- Space nodes ≥40px apart; wire paths need clearance
- Pin labels use engineering names: `I2C_SDA`, `CAN_H`, `CELL_SENSE`, `NTC_1`, `VDD`, `GND`
- **Do not leave generic labels** (`MCU`, `Cell Monitor IC`) when the user named parts — use `STM32F407`, `BQ76952`, etc. in `label` and `components.part`
- **Avoid overlapping nodes** — e.g. keep `memory` below `current_sensor` (different `y`, ≥80px apart)

## Topology customization (required)

Changing topology or chemistry is **not** a metadata-only edit. The UI renders `views.*.nodes` literally and also draws cell grids from `pack.topology`. You must update the schematic so different packs look different.

| Change | Required updates |
|--------|------------------|
| **Series count** (e.g. 4s → 12s) | `pack.cell_count`, `nominal_voltage_v`; pack `cells` label (e.g. `12S2P LFP Cell Stack`); widen pack `cells` node (`width` ≥ 120 + 12× per cell); AFE pin `CELL_1-N` and `cells_monitored`; temp `NTC_1-N` and `sensor_count` |
| **Parallel count** (e.g. 1p → 2p) | `pack.cell_count = series × parallel`; add pack `busbars` node for parallel strings; pack edges through busbars |
| **Chemistry** (NMC ↔ LFP) | `pack.chemistry`, correct `nominal_voltage_v`, OVP/UVP in `safety_rules.yaml` (LFP ~3.65V OVP, NMC ~4.25V) |
| **>16 series cells** | Add second `cell_monitor_ic` node (e.g. two LTC6811 or stacked BQ76952), split `CELL_1-8` / `CELL_9-16`, reposition nodes |
| **Part swap** | Update `components`, node `label`, and `component_ref` telemetry |

**Anti-pattern:** copying the 4s1p template and only changing `pack.topology`, `pack.chemistry`, and pin text while leaving the same node positions and a single AFE for 12s2p. That produces identical-looking diagrams.

**Checklist before finishing:**
- [ ] `pack.cell_count` equals series × parallel from topology string
- [ ] Pack `cells` label mentions topology + chemistry
- [ ] AFE `CELL_1-N` matches series count; `components.*.cells_monitored` matches
- [ ] Temp network `NTC_1-N` matches series (or user-specified sensor count)
- [ ] For 2p+, pack view includes `busbars` (or equivalent) node
- [ ] Part numbers visible in node labels and `components`

## safety_rules.yaml format

```yaml
- id: unique_rule_id
  condition: "expression string"
  action: "action string"
  component: mcu
  description: "Human-readable explanation"
```

Link `component: mcu` (or `memory`) so the UI shows rules when those blocks are selected. Never use hardware nicknames like `bq76952` or `cooling_fan` unless that is the node `id` in `views.bms`.

## Modification workflow

When user asks to change thresholds or improve safety:

1. Read current `bms/safety_rules.yaml` and `bms/architecture.bms.json`
2. Explain: **Current** → **Proposed** → **Reason**
3. Write updated files
4. Preserve valid layout; change only affected nodes/rules

## Minimal reference example (4s1p NMC)

Copy structure patterns from this example when creating new diagrams:

```json
{
  "schema_version": "1.0",
  "pack": {
    "topology": "4s1p",
    "cell_count": 4,
    "chemistry": "NMC",
    "nominal_voltage_v": 14.8
  },
  "views": {
    "pack": {
      "nodes": [
        { "id": "cells", "type": "cells", "label": "4S Cell Stack", "x": 80, "y": 320, "width": 200, "height": 80,
          "pins": [{ "id": "p1", "label": "B+", "side": "right" }] },
        { "id": "bms_board", "type": "bms_board", "label": "BMS Board", "x": 360, "y": 280, "width": 160, "height": 120,
          "drill_view": "bms", "pins": [
            { "id": "p1", "label": "PACK+", "side": "left" },
            { "id": "p2", "label": "CAN", "side": "right" }
          ] },
        { "id": "contactor", "type": "contactor", "label": "Contactor", "x": 580, "y": 300, "width": 100, "height": 80,
          "pins": [{ "id": "p1", "label": "LOAD", "side": "right" }] }
      ],
      "edges": [
        { "from_node": "cells", "from_pin": "p1", "to_node": "bms_board", "to_pin": "p1", "signal": "PACK+" },
        { "from_node": "bms_board", "from_pin": "p2", "to_node": "contactor", "to_pin": "p1", "signal": "MAIN" }
      ]
    },
    "bms": {
      "nodes": [
        { "id": "mcu", "type": "mcu", "label": "MCU", "x": 320, "y": 60, "width": 140, "height": 90,
          "component_ref": "mcu", "telemetry": { "cpu_pct": 32 },
          "pins": [
            { "id": "i2c", "label": "I2C", "side": "bottom" },
            { "id": "can", "label": "CAN", "side": "right" }
          ] },
        { "id": "cell_ic", "type": "cell_monitor_ic", "label": "Cell Monitor IC", "x": 80, "y": 220, "width": 160, "height": 80,
          "component_ref": "cell_monitor_0",
          "pins": [{ "id": "i2c", "label": "I2C", "side": "top" }, { "id": "cells", "label": "CELL_1-4", "side": "left" }] },
        { "id": "memory", "type": "memory", "label": "EEPROM / Flash", "x": 520, "y": 60, "width": 140, "height": 70,
          "component_ref": "memory",
          "pins": [{ "id": "spi", "label": "SPI", "side": "left" }] }
      ],
      "edges": [
        { "from_node": "mcu", "from_pin": "i2c", "to_node": "cell_ic", "to_pin": "i2c", "signal": "I2C_SDA" }
      ]
    }
  },
  "components": {
    "mcu": { "part": "STM32F407", "role": "protection_logic" },
    "cell_monitor_0": { "part": "BQ76952", "cells_monitored": 4 },
    "memory": { "part": "AT24C256", "role": "firmware_storage" }
  }
}
```

## Validation

Backend rejects invalid JSON/YAML on agent writes and UI saves. Common failures:

- Edge references unknown node or pin (e.g. `load` pin removed from `bms_board` but edge still uses it)
- Missing required BMS view node types (mcu, cell_monitor_ic, temperature_network, balancing, current_sensor, can_transceiver, memory)
- `safety_rules.yaml` wrapped in `rules:` instead of a top-level list

If a write fails, read the error message, fix the file, and retry with `write_file`.
