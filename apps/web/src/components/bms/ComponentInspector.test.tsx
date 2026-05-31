import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { parseArchitecture } from "../../lib/bms/layout";
import { ComponentInspector } from "./ComponentInspector";

const fixtureDir = join(dirname(fileURLToPath(import.meta.url)), "../../lib/bms/__fixtures__");
const fixture = readFileSync(join(fixtureDir, "architecture.bms.json"), "utf-8");

describe("ComponentInspector", () => {
  it("shows pack summary when no node selected", () => {
    const architecture = parseArchitecture(fixture)!;
    render(<ComponentInspector architecture={architecture} node={null} rules={[]} />);
    expect(screen.getByText("Pack overview")).toBeInTheDocument();
    expect(screen.getByText("4s1p")).toBeInTheDocument();
    expect(screen.getByText("14.8 V")).toBeInTheDocument();
  });

  it("shows telemetry for selected node", () => {
    const architecture = parseArchitecture(fixture)!;
    const mcu = architecture.views.bms.nodes.find((n) => n.id === "mcu")!;
    render(<ComponentInspector architecture={architecture} node={mcu} rules={[]} />);
    expect(screen.getByText("MCU")).toBeInTheDocument();
    expect(screen.getByText("32")).toBeInTheDocument();
  });

  it("shows component metadata from architecture.components", () => {
    const architecture = parseArchitecture(fixture)!;
    const mcu = architecture.views.bms.nodes.find((n) => n.id === "mcu")!;
    render(<ComponentInspector architecture={architecture} node={mcu} rules={[]} />);
    expect(screen.getByText("STM32F407")).toBeInTheDocument();
  });

  it("filters safety rules by component", () => {
    const architecture = parseArchitecture(fixture)!;
    const mcu = architecture.views.bms.nodes.find((n) => n.id === "mcu")!;
    const rules = [
      { id: "r1", condition: "a", action: "b", component: "mcu" },
      { id: "r2", condition: "c", action: "d", component: "memory" },
    ];
    render(<ComponentInspector architecture={architecture} node={mcu} rules={rules} />);
    expect(screen.getByText("r1")).toBeInTheDocument();
    expect(screen.queryByText("r2")).not.toBeInTheDocument();
  });
});
