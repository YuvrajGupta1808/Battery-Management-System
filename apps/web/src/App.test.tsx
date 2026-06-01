import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App routing", () => {
  it("renders the landing page at /", () => {
    window.history.replaceState({}, "", "/");
    render(<App />);
    expect(screen.getByRole("heading", { name: /design battery management systems/i })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /open workbench/i }).length).toBeGreaterThan(0);
  });

  it("navigates to the workbench from the landing page", () => {
    window.history.replaceState({}, "", "/");
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /start in the workbench/i }));
    expect(window.location.pathname).toBe("/workbench");
    expect(screen.getByRole("heading", { name: /CANary AI/i })).toBeInTheDocument();
  });

  it("returns home from the workbench", () => {
    window.history.replaceState({}, "", "/workbench");
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /back to home/i }));
    expect(window.location.pathname).toBe("/");
    expect(screen.getByRole("heading", { name: /design battery management systems/i })).toBeInTheDocument();
  });
});

describe("LandingPage content", () => {
  it("explains core CANary capabilities", () => {
    window.history.replaceState({}, "", "/");
    render(<App />);
    expect(screen.getByRole("heading", { name: /agent-authored diagrams/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /interactive svg schematics/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /schema-backed validation/i })).toBeInTheDocument();
  });

  it("links to the public demo slides deck", () => {
    window.history.replaceState({}, "", "/");
    render(<App />);
    const slidesLinks = screen.getAllByRole("link", { name: /demo slides/i });
    expect(slidesLinks.length).toBeGreaterThan(0);
    for (const link of slidesLinks) {
      expect(link).toHaveAttribute(
        "href",
        "https://docs.google.com/presentation/d/1CKAFcLRS_bu9ad1yHA_NGsjL9XdnqZ1kjYYGaqD6e_8/edit?usp=sharing",
      );
      expect(link).toHaveAttribute("target", "_blank");
    }
  });
});
