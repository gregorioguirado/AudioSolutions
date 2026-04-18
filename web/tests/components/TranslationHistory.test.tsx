import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import TranslationHistory from "@/components/TranslationHistory";

const rows = [
  {
    id: "a",
    source_console: "yamaha_cl",
    target_console: "digico_sd",
    source_model: "yamaha-cl5",
    target_model: "digico-sd12",
    source_filename: "festival.clf",
    channel_count: 72,
    translated_params: ["hpf", "eq"],
    approximated_params: [],
    dropped_params: ["premium_rack"],
    channel_names: ["KICK", "SNARE"],
    status: "complete",
    created_at: new Date().toISOString(),
  },
  {
    id: "b",
    source_console: "yamaha_cl",
    target_console: "digico_sd",
    source_model: "yamaha-ql5",
    target_model: "digico-sd12",
    source_filename: "monitor.clf",
    channel_count: 48,
    translated_params: ["hpf"],
    approximated_params: [],
    dropped_params: [],
    channel_names: [],
    status: "complete",
    created_at: new Date(Date.now() - 24 * 3600 * 1000).toISOString(),
  },
];

describe("TranslationHistory", () => {
  it("renders a row per translation with summary chips", () => {
    render(<TranslationHistory translations={rows} />);
    expect(screen.getByText("festival.clf")).toBeInTheDocument();
    expect(screen.getByText("monitor.clf")).toBeInTheDocument();
    expect(screen.getByText(/✓ 2/)).toBeInTheDocument();
    expect(screen.getByText(/× 1/)).toBeInTheDocument();
  });

  it("renders empty state when no translations", () => {
    render(<TranslationHistory translations={[]} />);
    expect(screen.getByText(/No translations yet/i)).toBeInTheDocument();
  });

  it("clicking a row opens the ReportPane", () => {
    render(<TranslationHistory translations={rows} />);
    // ReportPane not present initially
    expect(screen.queryByRole("button", { name: /close/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("festival.clf"));
    expect(screen.getByRole("button", { name: /close/i })).toBeInTheDocument();
  });
});
