import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BmsDiagramPlaceholder } from "./BmsDiagramPlaceholder";

describe("BmsDiagramPlaceholder", () => {
  it("explains when template preview is unavailable", () => {
    render(
      <BmsDiagramPlaceholder
        state={{ kind: "template" }}
        selectedPath="bms/templates/architecture.template.bms.json"
      />,
    );
    expect(screen.getByText(/Could not preview this template/i)).toBeInTheDocument();
    expect(screen.getByText("Template unavailable")).toBeInTheDocument();
  });

  it("explains empty primary architecture", () => {
    render(
      <BmsDiagramPlaceholder
        state={{
          kind: "empty",
          path: "bms/architecture.bms.json",
          architecture: {
            schema_version: "1.0",
            pack: { topology: "4s1p", cell_count: 4, chemistry: "NMC", nominal_voltage_v: 14.8 },
            views: { pack: { nodes: [], edges: [] }, bms: { nodes: [], edges: [] } },
          },
        }}
        selectedPath="bms/architecture.bms.json"
      />,
    );
    expect(screen.getByText(/no diagram nodes yet/i)).toBeInTheDocument();
  });
});
