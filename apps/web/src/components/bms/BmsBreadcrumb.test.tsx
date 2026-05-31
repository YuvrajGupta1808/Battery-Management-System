import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BmsBreadcrumb } from "./BmsBreadcrumb";

describe("BmsBreadcrumb", () => {
  it("shows pack only on pack view", () => {
    render(<BmsBreadcrumb activeView="pack" onNavigate={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Pack" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "BMS" })).not.toBeInTheDocument();
  });

  it("shows pack and BMS on bms view", () => {
    render(<BmsBreadcrumb activeView="bms" onNavigate={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Pack" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "BMS" })).toBeInTheDocument();
  });

  it("shows selected node label", () => {
    render(<BmsBreadcrumb activeView="bms" selectedNodeLabel="MCU" onNavigate={vi.fn()} />);
    expect(screen.getByText("MCU")).toBeInTheDocument();
  });

  it("calls onNavigate when pack clicked", () => {
    const onNavigate = vi.fn();
    render(<BmsBreadcrumb activeView="bms" onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("button", { name: "Pack" }));
    expect(onNavigate).toHaveBeenCalledWith("pack");
  });
});
