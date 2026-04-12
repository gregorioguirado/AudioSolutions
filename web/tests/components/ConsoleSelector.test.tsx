import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ConsoleSelector from "../../src/components/ConsoleSelector";

describe("ConsoleSelector", () => {
  it("renders source and target dropdowns", () => {
    render(
      <ConsoleSelector source="yamaha_cl" target="digico_sd" onSourceChange={() => {}} onTargetChange={() => {}} />
    );
    expect(screen.getByLabelText(/from/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/to/i)).toBeInTheDocument();
  });

  it("shows Yamaha CL/QL as source option", () => {
    render(
      <ConsoleSelector source="yamaha_cl" target="digico_sd" onSourceChange={() => {}} onTargetChange={() => {}} />
    );
    const sourceSelect = screen.getByLabelText(/from/i) as HTMLSelectElement;
    expect(sourceSelect.value).toBe("yamaha_cl");
  });

  it("calls onSourceChange when source is changed", async () => {
    const user = userEvent.setup();
    const onSourceChange = vi.fn();
    render(
      <ConsoleSelector source="yamaha_cl" target="digico_sd" onSourceChange={onSourceChange} onTargetChange={() => {}} />
    );
    await user.selectOptions(screen.getByLabelText(/from/i), "digico_sd");
    expect(onSourceChange).toHaveBeenCalledWith("digico_sd");
  });
});
