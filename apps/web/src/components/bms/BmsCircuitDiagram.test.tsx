import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { parseArchitecture } from "../../lib/bms/layout";
import { BmsCircuitDiagram } from "./BmsCircuitDiagram";

const fixtureDir = join(dirname(fileURLToPath(import.meta.url)), "../../lib/bms/__fixtures__");
const fixture = readFileSync(join(fixtureDir, "architecture.bms.json"), "utf-8");

describe("BmsCircuitDiagram", () => {
  it("renders pack view nodes", () => {
    const architecture = parseArchitecture(fixture)!;
    render(<BmsCircuitDiagram architecture={architecture} safetyRules={[]} />);
    expect(screen.getByText("BMS Board")).toBeInTheDocument();
    expect(screen.getByText("4S NMC Stack")).toBeInTheDocument();
  });

  it("shows pack summary in inspector", () => {
    const architecture = parseArchitecture(fixture)!;
    render(<BmsCircuitDiagram architecture={architecture} safetyRules={[]} />);
    expect(screen.getAllByText("4s1p").length).toBeGreaterThan(0);
    expect(screen.getAllByText("NMC").length).toBeGreaterThan(0);
  });

  it("drills into BMS view when BMS Board clicked", () => {
    const architecture = parseArchitecture(fixture)!;
    render(<BmsCircuitDiagram architecture={architecture} safetyRules={[]} />);

    fireEvent.click(screen.getByText("BMS Board"));

    expect(screen.getByRole("button", { name: "BMS" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Cell Monitor AFE/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /BQ76952/ })).toBeInTheDocument();
    expect(screen.queryByText("4S NMC Stack")).not.toBeInTheDocument();
  });

  it("navigates back to pack via breadcrumb", () => {
    const architecture = parseArchitecture(fixture)!;
    render(<BmsCircuitDiagram architecture={architecture} safetyRules={[]} />);

    fireEvent.click(screen.getByText("BMS Board"));
    fireEvent.click(screen.getByRole("button", { name: "Pack" }));

    expect(screen.getByText("4S NMC Stack")).toBeInTheDocument();
  });

  it("shows safety rules when MCU selected in BMS view", () => {
    const architecture = parseArchitecture(fixture)!;
    const rules = [
      {
        id: "thermal_fan_on",
        condition: "pack_temp_c > 80",
        action: "cooling.fan = ON",
        component: "mcu",
      },
    ];
    render(<BmsCircuitDiagram architecture={architecture} safetyRules={rules} />);

    fireEvent.click(screen.getByText("BMS Board"));
    fireEvent.click(screen.getByRole("button", { name: /MCU · STM32F407|STM32F407/ }));

    expect(screen.getByText("thermal_fan_on")).toBeInTheDocument();
    expect(screen.getByText("pack_temp_c > 80")).toBeInTheDocument();
  });

  it("renders wire signal labels from fixture", () => {
    const architecture = parseArchitecture(fixture)!;
    const { container } = render(<BmsCircuitDiagram architecture={architecture} safetyRules={[]} />);
    fireEvent.click(screen.getByText("BMS Board"));
    expect(container.querySelector(".schematic-wire-label")).toBeTruthy();
  });
});
