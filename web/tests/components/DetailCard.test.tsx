import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import DetailCard from "@/components/DetailCard";
import { getModelById } from "@/lib/constants";

describe("DetailCard", () => {
  it("renders source card with detected footer", () => {
    const cl5 = getModelById("yamaha-cl5")!;
    render(<DetailCard model={cl5} role="source" />);
    expect(screen.getByText("CL5")).toBeInTheDocument();
    expect(screen.getByText(/CL Series/i)).toBeInTheDocument();
    expect(screen.getByText(".clf")).toBeInTheDocument();
    expect(screen.getByText(/Detected from file/i)).toBeInTheDocument();
  });

  it("renders target card with supported footer", () => {
    const sd12 = getModelById("digico-sd12")!;
    render(<DetailCard model={sd12} role="target" />);
    expect(screen.getByText("SD12")).toBeInTheDocument();
    expect(screen.getByText(/Supported/i)).toBeInTheDocument();
  });

  it("does NOT render maxChannels or mixBuses numeric rows", () => {
    const cl5 = getModelById("yamaha-cl5")!;
    render(<DetailCard model={cl5} role="source" />);
    expect(screen.queryByText(/Max channels/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Mix buses/i)).not.toBeInTheDocument();
  });

  it("renders placeholder when no model selected", () => {
    render(<DetailCard model={undefined} role="target" />);
    expect(screen.getByText(/Select a target console/i)).toBeInTheDocument();
  });
});
