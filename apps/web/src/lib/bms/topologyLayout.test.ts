import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { parseArchitecture } from "./layout";
import {
  adaptArchitectureForTopology,
  afeBlockDimensions,
  cellStackDimensions,
} from "./topologyLayout";

const fixtureDir = join(dirname(fileURLToPath(import.meta.url)), "__fixtures__");
const fixture = readFileSync(join(fixtureDir, "architecture.bms.json"), "utf-8");

describe("cellStackDimensions", () => {
  it("scales width with series count", () => {
    expect(cellStackDimensions(4, 1).width).toBeLessThan(cellStackDimensions(12, 1).width);
    expect(cellStackDimensions(12, 2).height).toBeGreaterThan(cellStackDimensions(12, 1).height);
  });
});

describe("adaptArchitectureForTopology", () => {
  it("widens pack cells block for 12s vs 4s", () => {
    const base = parseArchitecture(fixture)!;
    const fourS = adaptArchitectureForTopology(base);
    const twelveS = adaptArchitectureForTopology({
      ...base,
      pack: { ...base.pack, topology: "12s1p", cell_count: 12, nominal_voltage_v: 38.4 },
    });

    const cells4 = fourS.views.pack.nodes.find((n) => n.type === "cells")!;
    const cells12 = twelveS.views.pack.nodes.find((n) => n.type === "cells")!;

    expect(cells12.width).toBeGreaterThan(cells4.width);
    expect(cells12.label).toContain("12S");
  });

  it("expands AFE block and syncs CELL pins for higher series", () => {
    const base = parseArchitecture(fixture)!;
    const adapted = adaptArchitectureForTopology({
      ...base,
      pack: { ...base.pack, topology: "12s1p", cell_count: 12 },
    });

    const afe = adapted.views.bms.nodes.find((n) => n.type === "cell_monitor_ic")!;
    const fourDims = afeBlockDimensions(4);
    const twelveDims = afeBlockDimensions(12);

    expect(afe.width).toBe(twelveDims.width);
    expect(twelveDims.width).toBeGreaterThan(fourDims.width);
    const cellPin = afe.pins?.find((p) => /^CELL_/i.test(p.label));
    expect(cellPin?.label).toBe("CELL_1-12");
    expect(afe.telemetry?.cells_monitored).toBe(12);
  });

  it("injects second AFE for 24s packs", () => {
    const base = parseArchitecture(fixture)!;
    const adapted = adaptArchitectureForTopology({
      ...base,
      pack: { ...base.pack, topology: "24s1p", cell_count: 24, nominal_voltage_v: 76.8 },
    });

    const second = adapted.views.bms.nodes.find((n) => n.id === "cell_ic_2");
    expect(second).toBeDefined();
    expect(second?.pins?.find((p) => p.id === "cell_sense")?.label).toBe("CELL_17-24");
  });
});
