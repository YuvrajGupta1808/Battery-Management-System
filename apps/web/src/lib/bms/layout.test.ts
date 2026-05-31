import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import {
  isBmsArchitecturePath,
  isBmsTemplatePath,
  isPrimaryArchitecturePath,
  isRenderableArchitecture,
  manhattanPath,
  nodeShowsRules,
  parseArchitecture,
  parseArchitecturePreview,
  parsePackTopology,
  parseSafetyRules,
  pinPosition,
  resolveComponentPart,
  resolveDiagramState,
  seriesCellPinLabel,
  viewBounds,
} from "./layout";

const fixtureDir = join(dirname(fileURLToPath(import.meta.url)), "__fixtures__");
const fixture = readFileSync(join(fixtureDir, "architecture.bms.json"), "utf-8");

describe("diagram paths", () => {
  it("excludes template paths from diagram candidates", () => {
    expect(isBmsTemplatePath("bms/templates/architecture.template.bms.json")).toBe(true);
    expect(isBmsArchitecturePath("bms/templates/architecture.template.bms.json")).toBe(false);
    expect(isPrimaryArchitecturePath("bms/architecture.bms.json")).toBe(true);
  });

  it("resolveDiagramState detects template", () => {
    const state = resolveDiagramState("bms/templates/architecture.template.bms.json", "{}");
    expect(state.kind).toBe("template");
  });

  it("resolveDiagramState detects empty architecture", () => {
    const content = JSON.stringify({
      schema_version: "1.0",
      pack: { topology: "4s1p", cell_count: 4, chemistry: "NMC", nominal_voltage_v: 14.8 },
      views: { pack: { nodes: [], edges: [] }, bms: { nodes: [], edges: [] } },
    });
    expect(resolveDiagramState("bms/architecture.bms.json", content).kind).toBe("empty");
  });
});

describe("parseArchitecturePreview", () => {
  it("strips template_meta before validating", () => {
    const withMeta = JSON.parse(fixture) as Record<string, unknown>;
    withMeta.template_meta = { purpose: "test" };
    const arch = parseArchitecturePreview(JSON.stringify(withMeta));
    expect(arch).not.toBeNull();
    expect(arch?.pack.topology).toBe("4s1p");
  });
});

describe("isRenderableArchitecture", () => {
  it("accepts valid fixture shape", () => {
    expect(isRenderableArchitecture(JSON.parse(fixture))).toBe(true);
  });

  it("rejects missing edges array", () => {
    const data = JSON.parse(fixture) as Record<string, unknown>;
    const views = data.views as Record<string, { nodes: unknown[] }>;
    views.pack = { nodes: views.pack.nodes } as typeof views.pack;
    expect(isRenderableArchitecture(data)).toBe(false);
  });
});

describe("parseArchitecture", () => {
  it("returns null for invalid JSON", () => {
    expect(parseArchitecture("{bad")).toBeNull();
  });

  it("returns null for JSON missing views", () => {
    expect(
      parseArchitecture(
        JSON.stringify({
          schema_version: "1.0",
          pack: { topology: "4s1p", cell_count: 4, chemistry: "NMC", nominal_voltage_v: 14.8 },
        }),
      ),
    ).toBeNull();
  });

  it("parses valid fixture", () => {
    const arch = parseArchitecture(fixture);
    expect(arch?.schema_version).toBe("1.0");
    expect(arch?.views.bms.nodes.some((n) => n.type === "mcu")).toBe(true);
  });
});

describe("parseSafetyRules", () => {
  it("parses multiple rules with comments", () => {
    const yaml = `# comment
- id: rule_a
  condition: "a > 1"
  action: "do_a()"
  component: mcu
- id: rule_b
  condition: "b > 2"
  action: "do_b()"
`;
    const rules = parseSafetyRules(yaml);
    expect(rules).toHaveLength(2);
    expect(rules[0].id).toBe("rule_a");
    expect(rules[1].component).toBeUndefined();
  });

  it("strips quoted scalars", () => {
    const rules = parseSafetyRules(`- id: x
  condition: "temp > 80"
  action: "fan.on()"
`);
    expect(rules[0].condition).toBe("temp > 80");
  });

  it("returns empty array for empty content", () => {
    expect(parseSafetyRules("")).toEqual([]);
  });
});

describe("pinPosition", () => {
  it("places left pins on left edge", () => {
    const arch = parseArchitecture(fixture)!;
    const node = arch.views.pack.nodes.find((n) => n.id === "bms_board")!;
    const pin = node.pins![0];
    const pos = pinPosition(node, pin);
    expect(pos.x).toBe(node.x);
  });

  it("places right pins on right edge", () => {
    const arch = parseArchitecture(fixture)!;
    const node = arch.views.pack.nodes.find((n) => n.id === "bms_board")!;
    const pin = node.pins!.find((p) => p.side === "right")!;
    const pos = pinPosition(node, pin);
    expect(pos.x).toBe(node.x + node.width);
  });

  it("spaces multiple pins on same side", () => {
    const arch = parseArchitecture(fixture)!;
    const mcu = arch.views.bms.nodes.find((n) => n.id === "mcu")!;
    const pins = mcu.pins!.filter((p) => p.side === "bottom");
    if (pins.length >= 1) {
      const pos = pinPosition(mcu, pins[0]);
      expect(pos.y).toBe(mcu.y + mcu.height);
    }
  });
});

describe("manhattanPath", () => {
  it("returns SVG path with moveto and lineto", () => {
    const d = manhattanPath({ x: 0, y: 0 }, { x: 100, y: 50 }, "right", "left");
    expect(d).toMatch(/^M /);
    expect(d).toContain("L ");
  });
});

describe("viewBounds", () => {
  it("returns defaults for empty nodes", () => {
    expect(viewBounds([])).toEqual({ width: 800, height: 480 });
  });

  it("includes padding", () => {
    const arch = parseArchitecture(fixture)!;
    const bounds = viewBounds(arch.views.pack.nodes, 40);
    const maxX = Math.max(...arch.views.pack.nodes.map((n) => n.x + n.width));
    expect(bounds.width).toBe(maxX + 40);
  });
});

describe("isBmsArchitecturePath", () => {
  it("detects .bms.json paths", () => {
    expect(isBmsArchitecturePath("bms/architecture.bms.json")).toBe(true);
    expect(isBmsArchitecturePath("README.md")).toBe(false);
    expect(isBmsArchitecturePath("bms/safety_rules.yaml")).toBe(false);
  });
});

describe("nodeShowsRules", () => {
  it("returns true for mcu and memory", () => {
    expect(nodeShowsRules({ id: "1", type: "mcu", label: "M", x: 0, y: 0, width: 80, height: 60 })).toBe(true);
    expect(nodeShowsRules({ id: "2", type: "memory", label: "M", x: 0, y: 0, width: 80, height: 60 })).toBe(true);
    expect(nodeShowsRules({ id: "3", type: "can_transceiver", label: "C", x: 0, y: 0, width: 80, height: 60 })).toBe(
      false,
    );
  });
});

describe("parsePackTopology", () => {
  it("parses series and parallel counts", () => {
    expect(parsePackTopology("4s1p")).toEqual({ series: 4, parallel: 1 });
    expect(parsePackTopology("12S2P")).toEqual({ series: 12, parallel: 2 });
  });

  it("returns null for invalid topology", () => {
    expect(parsePackTopology("12S")).toBeNull();
  });
});

describe("seriesCellPinLabel", () => {
  it("formats cell sense pin labels", () => {
    expect(seriesCellPinLabel(4)).toBe("CELL_1-4");
    expect(seriesCellPinLabel(1)).toBe("CELL_1");
  });
});

describe("resolveComponentPart", () => {
  it("reads part numbers from components map", () => {
    expect(resolveComponentPart("mcu", { mcu: { part: "STM32F407" } })).toBe("STM32F407");
    expect(resolveComponentPart("missing", { mcu: { part: "STM32F407" } })).toBeNull();
  });
});

describe("fixture integrity", () => {
  it("has drill_view on bms_board", () => {
    const arch = parseArchitecture(fixture)!;
    const board = arch.views.pack.nodes.find((n) => n.id === "bms_board");
    expect(board?.drill_view).toBe("bms");
  });

  it("has wired edges in bms view", () => {
    const arch = parseArchitecture(fixture)!;
    expect(arch.views.bms.edges.length).toBeGreaterThan(0);
    expect(arch.views.bms.edges[0].signal).toBeTruthy();
  });
});
