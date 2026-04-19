import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import DownloadAcknowledgement from "@/components/DownloadAcknowledgement";

const LINKS = [
  {
    href: "/api/download/abc?type=output",
    label: "Download translated file",
    variant: "primary" as const,
  },
  {
    href: "/api/download/abc?type=report",
    label: "Download translation report (PDF)",
    variant: "secondary" as const,
  },
];

describe("DownloadAcknowledgement", () => {
  it("disables every download button until the acknowledgement checkbox is checked", () => {
    render(<DownloadAcknowledgement links={LINKS} />);

    // Pre-check: download buttons render as disabled <button> elements,
    // not as <a> links — so they cannot navigate.
    const fileButton = screen.getByRole("button", { name: /download translated file/i });
    const reportButton = screen.getByRole("button", {
      name: /download translation report \(pdf\)/i,
    });
    expect(fileButton).toBeDisabled();
    expect(reportButton).toBeDisabled();

    // No <a> elements exist for the downloads yet.
    expect(screen.queryByRole("link", { name: /download translated file/i })).toBeNull();
    expect(
      screen.queryByRole("link", { name: /download translation report \(pdf\)/i }),
    ).toBeNull();
  });

  it("enables (and turns into real links) once the checkbox is checked", () => {
    render(<DownloadAcknowledgement links={LINKS} />);

    const checkbox = screen.getByRole("checkbox", {
      name: /verified on the target console before any live performance/i,
    });
    expect(checkbox).not.toBeChecked();

    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();

    const fileLink = screen.getByRole("link", { name: /download translated file/i });
    const reportLink = screen.getByRole("link", {
      name: /download translation report \(pdf\)/i,
    });
    expect(fileLink).toHaveAttribute("href", "/api/download/abc?type=output");
    expect(reportLink).toHaveAttribute("href", "/api/download/abc?type=report");

    // The disabled buttons are gone.
    expect(
      screen.queryByRole("button", { name: /download translated file/i }),
    ).toBeNull();
  });

  it("re-disables downloads if the checkbox is unchecked again", () => {
    render(<DownloadAcknowledgement links={LINKS} />);

    const checkbox = screen.getByRole("checkbox", {
      name: /verified on the target console before any live performance/i,
    });

    fireEvent.click(checkbox);
    expect(screen.getByRole("link", { name: /download translated file/i })).toBeInTheDocument();

    fireEvent.click(checkbox);
    expect(checkbox).not.toBeChecked();
    expect(screen.queryByRole("link", { name: /download translated file/i })).toBeNull();
    expect(
      screen.getByRole("button", { name: /download translated file/i }),
    ).toBeDisabled();
  });
});
