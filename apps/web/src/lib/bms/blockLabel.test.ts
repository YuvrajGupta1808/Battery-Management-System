import { describe, expect, it } from "vitest";

import {
  formatBlockDisplayLabel,
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

describe("truncateLabel", () => {
  it("adds ellipsis when over limit", () => {
    expect(truncateLabel("abcdefghij", 8)).toBe("abcdefg…");
  });
});
