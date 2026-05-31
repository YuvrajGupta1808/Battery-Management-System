import { describe, expect, it } from "vitest";

import {
  formatBlockDisplayLabel,
  formatSchematicBlockLabels,
  parseLabelParts,
  truncateLabel,
} from "./blockLabel";

describe("parseLabelParts", () => {
  it("splits on en-dash", () => {
    expect(parseLabelParts("MCU – STM32F407")).toEqual({
      title: "MCU",
      detail: "STM32F407",
    });
  });

  it("folds short parentheticals into detail", () => {
    const parts = parseLabelParts("Cell Monitor – BQ76952 (CELL_1-12)");
    expect(parts.title).toBe("Cell Monitor");
    expect(parts.detail).toContain("BQ76952");
    expect(parts.detail).toContain("CELL_1-12");
  });
});

describe("formatBlockDisplayLabel", () => {
  it("splits long agent labels into title and detail lines", () => {
    const long =
      "Temp Network – NTC_1 to NTC_12 (Murata NCP18WM223J03RL)";
    const { lines } = formatBlockDisplayLabel(long, 150);
    expect(lines[0]).toBe("Temp Network");
    expect(lines[1]).toContain("NTC_1");
    expect(lines[1]!.length).toBeLessThan(long.length);
  });

  it("uses part ref when label has no detail", () => {
    const { lines } = formatBlockDisplayLabel("MCU", 120, { partNumber: "STM32F407" });
    expect(lines).toEqual(["MCU", "STM32F407"]);
  });
});

describe("formatSchematicBlockLabels", () => {
  it("shows role, part, and metadata for MCU", () => {
    const { lines } = formatSchematicBlockLabels("mcu", "STM32F407", 160, {
      partNumber: "STM32F407",
      componentMeta: { part: "STM32F407", role: "protection_logic" },
    });
    expect(lines[0]?.text).toBe("MCU");
    expect(lines[0]?.variant).toBe("title");
    expect(lines[1]?.text).toBe("STM32F407");
    expect(lines[1]?.variant).toBe("part");
    expect(lines[2]?.text).toBe("protection logic");
  });

  it("shows role and part for cell monitor", () => {
    const { lines } = formatSchematicBlockLabels("cell_monitor_ic", "Cell Monitor IC", 180, {
      partNumber: "BQ76952",
      componentMeta: { cells_monitored: 12 },
    });
    expect(lines[0]?.text).toBe("Cell Monitor AFE");
    expect(lines[1]?.text).toBe("BQ76952");
    expect(lines[2]?.text).toBe("12S monitored");
  });
});

describe("truncateLabel", () => {
  it("adds ellipsis when over limit", () => {
    expect(truncateLabel("abcdefghij", 8)).toBe("abcdefg…");
  });
});
