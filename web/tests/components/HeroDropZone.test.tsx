import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import HeroDropZone from "../../src/components/HeroDropZone";

describe("HeroDropZone", () => {
  it("renders the headline", () => {
    render(<HeroDropZone />);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading).toHaveTextContent(/stop rebuilding/i);
    expect(heading).toHaveTextContent(/your shows/i);
  });

  it("renders the drop zone prompt", () => {
    render(<HeroDropZone />);
    expect(screen.getByText(/drop .cle here/i)).toBeInTheDocument();
  });

  it("renders the translation preview panels", () => {
    render(<HeroDropZone />);
    expect(screen.getByText(/yamaha cl5/i)).toBeInTheDocument();
    expect(screen.getByText(/digico sd12/i)).toBeInTheDocument();
  });

  it("renders channel names in the preview", () => {
    render(<HeroDropZone />);
    expect(screen.getAllByText(/kick/i).length).toBeGreaterThanOrEqual(2);
  });
});
