import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SafetyRulesPanel } from "./SafetyRulesPanel";

describe("SafetyRulesPanel", () => {
  it("shows empty state when no rules", () => {
    render(<SafetyRulesPanel rules={[]} />);
    expect(screen.getByText(/No safety rules linked/)).toBeInTheDocument();
  });

  it("renders rule condition and action", () => {
    render(
      <SafetyRulesPanel
        rules={[
          {
            id: "thermal_fan_on",
            condition: "pack_temp_c > 80",
            action: "cooling.fan = ON",
            description: "Enable cooling fan",
          },
        ]}
      />,
    );
    expect(screen.getByText("thermal_fan_on")).toBeInTheDocument();
    expect(screen.getByText("pack_temp_c > 80")).toBeInTheDocument();
    expect(screen.getByText("cooling.fan = ON")).toBeInTheDocument();
    expect(screen.getByText("Enable cooling fan")).toBeInTheDocument();
  });

  it("uses custom title", () => {
    render(<SafetyRulesPanel rules={[]} title="Protection Logic" />);
    expect(screen.getByText("Protection Logic")).toBeInTheDocument();
  });
});
