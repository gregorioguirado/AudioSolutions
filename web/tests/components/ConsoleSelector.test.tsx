import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ConsoleSelector from "@/components/ConsoleSelector";
import { getModelById } from "@/lib/constants";

describe("ConsoleSelector (new)", () => {
  it("renders two panels with labels", () => {
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd12"
        onSourceChange={vi.fn()}
        onTargetChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/Source Console/i)).toBeInTheDocument();
    expect(screen.getByText(/Target Console/i)).toBeInTheDocument();
  });

  it("shows the Auto-detected banner on the source side when sourceDetected is true", () => {
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd12"
        onSourceChange={vi.fn()}
        onTargetChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/Auto-detected/i)).toBeInTheDocument();
    expect(screen.getByText(/Override/i)).toBeInTheDocument();
  });

  it("clicking a brand in the target sidebar changes which models are listed", () => {
    const onTargetChange = vi.fn();
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd12"
        onSourceChange={vi.fn()}
        onTargetChange={onTargetChange}
      />,
    );
    // Target side starts on DiGiCo — SD12 chip visible.
    // (SD12 appears in both the chip button and the DetailCard header, so assert ≥1.)
    expect(screen.getAllByText("SD12").length).toBeGreaterThan(0);
    // Click Yamaha on the target sidebar (pick the rightmost "Yamaha" button).
    const yamahaButtons = screen.getAllByText("Yamaha");
    fireEvent.click(yamahaButtons[yamahaButtons.length - 1]);
    // Now Yamaha CL/QL models appear on the target side.
    expect(screen.getAllByText("CL5").length).toBeGreaterThan(0);
    expect(screen.getAllByText("QL5").length).toBeGreaterThan(0);
  });

  it("clicking a target model chip invokes onTargetChange", () => {
    const onTargetChange = vi.fn();
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd12"
        onSourceChange={vi.fn()}
        onTargetChange={onTargetChange}
      />,
    );
    fireEvent.click(screen.getByText("Quantum 338"));
    expect(onTargetChange).toHaveBeenCalledWith("digico-quantum-338");
  });

  it("chips show only the model name — no channel number", () => {
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd12"
        onSourceChange={vi.fn()}
        onTargetChange={vi.fn()}
      />,
    );
    // The chip text for SD12 should NOT contain "96 ch" or similar.
    // SD12 appears in both the chip (button) and the DetailCard header (h4);
    // pick the one inside a <button> to target the chip specifically.
    const sd12Nodes = screen.getAllByText("SD12");
    const chip = sd12Nodes.map((n) => n.closest("button")).find((b) => b !== null);
    expect(chip).not.toBeNull();
    expect(chip?.textContent).not.toMatch(/ch\b/i);
  });

  it("detail cards appear under each panel", () => {
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd12"
        onSourceChange={vi.fn()}
        onTargetChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/Detected from file/i)).toBeInTheDocument();
    expect(screen.getByText(/Supported/i)).toBeInTheDocument();
  });
});
