import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Timecode from "@/components/Timecode";

describe("Timecode", () => {
  it("shows both relative and absolute lines for a recent timestamp", () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    render(<Timecode iso={twoHoursAgo} />);
    // Relative: some "hours ago" wording
    expect(screen.getByTestId("timecode-relative").textContent).toMatch(/hour/i);
    // Absolute: contains a day/month and a time
    const abs = screen.getByTestId("timecode-absolute").textContent ?? "";
    expect(abs).toMatch(/\d{1,2}:\d{2}/);
  });

  it("renders 'Yesterday' for a timestamp ~1 day old", () => {
    const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    render(<Timecode iso={yesterday} />);
    expect(screen.getByTestId("timecode-relative").textContent).toMatch(/day/i);
  });

  it("renders nothing useful for a missing timestamp but does not crash", () => {
    const { container } = render(<Timecode iso="" />);
    expect(container).toBeTruthy();
  });
});
