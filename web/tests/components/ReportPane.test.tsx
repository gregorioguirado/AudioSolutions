import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ReportPane from "@/components/ReportPane";

const baseTranslation = {
  id: "t1",
  source_console: "yamaha_cl",
  target_console: "digico_sd",
  source_model: "yamaha-cl5",
  target_model: "digico-sd12",
  source_filename: "festival.clf",
  channel_count: 72,
  translated_params: ["channel_names", "hpf", "eq_4_band"],
  approximated_params: ["eq_q_bands_3_4"],
  dropped_params: ["premium_rack"],
  channel_names: ["KICK", "SNARE TOP", "BASS DI"],
  status: "complete",
  created_at: new Date().toISOString(),
};

describe("ReportPane", () => {
  it("renders filename and route subtitle", () => {
    render(<ReportPane translation={baseTranslation} onClose={vi.fn()} />);
    expect(screen.getByText("festival.clf")).toBeInTheDocument();
    expect(screen.getByText(/72 ch/i)).toBeInTheDocument();
  });

  it("shows summary chips with counts", () => {
    render(<ReportPane translation={baseTranslation} onClose={vi.fn()} />);
    expect(screen.getByText(/✓ 3/)).toBeInTheDocument();
    expect(screen.getByText(/~ 1/)).toBeInTheDocument();
    expect(screen.getByText(/× 1/)).toBeInTheDocument();
  });

  it("lists translated / approximated / dropped params", () => {
    render(<ReportPane translation={baseTranslation} onClose={vi.fn()} />);
    expect(screen.getByText(/Channel Names/i)).toBeInTheDocument(); // section label
    expect(screen.getByText(/Hpf/i)).toBeInTheDocument();
    expect(screen.getByText(/Premium Rack/i)).toBeInTheDocument();
  });

  it("renders channel name cells", () => {
    render(<ReportPane translation={baseTranslation} onClose={vi.fn()} />);
    expect(screen.getByText("KICK")).toBeInTheDocument();
    expect(screen.getByText("SNARE TOP")).toBeInTheDocument();
  });

  it("shows a graceful fallback when channel_names is empty", () => {
    render(
      <ReportPane
        translation={{ ...baseTranslation, channel_names: [] }}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/Channel names not stored/i)).toBeInTheDocument();
  });

  it("calls onClose when the ✕ is clicked", () => {
    const onClose = vi.fn();
    render(<ReportPane translation={baseTranslation} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalled();
  });
});
