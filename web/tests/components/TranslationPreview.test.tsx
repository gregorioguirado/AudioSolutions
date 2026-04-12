import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import TranslationPreview from "../../src/components/TranslationPreview";

const MOCK_DATA = {
  channelCount: 3,
  translatedParams: ["channel_names", "hpf"],
  approximatedParams: ["eq_band_types"],
  droppedParams: ["yamaha_premium_rack"],
  channels: [
    { name: "KICK", status: "translated" as const },
    { name: "SNARE", status: "approximated" as const },
    { name: "KEYS", status: "dropped" as const },
  ],
};

describe("TranslationPreview", () => {
  it("renders the channel count", () => {
    render(<TranslationPreview {...MOCK_DATA} />);
    expect(screen.getByText(/3 channels/i)).toBeInTheDocument();
  });

  it("renders channel names", () => {
    render(<TranslationPreview {...MOCK_DATA} />);
    expect(screen.getByText("KICK")).toBeInTheDocument();
    expect(screen.getByText("SNARE")).toBeInTheDocument();
    expect(screen.getByText("KEYS")).toBeInTheDocument();
  });

  it("renders parameter summary sections", () => {
    render(<TranslationPreview {...MOCK_DATA} />);
    expect(screen.getByText(/✓ Translated/)).toBeInTheDocument();
    expect(screen.getByText(/~ Approximated/)).toBeInTheDocument();
    expect(screen.getByText(/× Dropped/)).toBeInTheDocument();
  });
});
