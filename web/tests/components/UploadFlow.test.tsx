import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import UploadFlow from "@/components/UploadFlow";

function fileWithName(name: string) {
  return new File(["dummy"], name, { type: "application/octet-stream" });
}

describe("UploadFlow (file-first)", () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  it("shows only the dropzone in State A (no file)", () => {
    render(<UploadFlow />);
    expect(screen.getByText(/Drop your show file/i)).toBeInTheDocument();
    // Selector not visible yet
    expect(screen.queryByText(/Source Console/i)).not.toBeInTheDocument();
  });

  it("after selecting a .clf file, the selector appears with Yamaha CL5 auto-detected", () => {
    render(<UploadFlow />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(input, "files", {
      value: [fileWithName("show.clf")],
      configurable: true,
    });
    fireEvent.change(input);

    expect(screen.getByText(/Source Console/i)).toBeInTheDocument();
    expect(screen.getByText(/Auto-detected/i)).toBeInTheDocument();
    // CL5 chip is active - there may be multiple "CL5" matches (chip + detail card h4)
    expect(screen.getAllByText("CL5").length).toBeGreaterThan(0);
    // Translate button appears
    expect(screen.getByRole("button", { name: /Translate/i })).toBeInTheDocument();
  });

  it("uploading calls /api/translate with both model and brand ids", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({
        translationId: "t1",
        channelCount: 72,
        translatedParams: [],
        approximatedParams: [],
        droppedParams: [],
        authenticated: true,
      }),
    } as unknown as Response);

    render(<UploadFlow />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(input, "files", {
      value: [fileWithName("show.clf")],
      configurable: true,
    });
    fireEvent.change(input);

    fireEvent.click(screen.getByRole("button", { name: /Translate/i }));

    // Give the fetch a tick
    await Promise.resolve();

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/translate",
      expect.objectContaining({ method: "POST" }),
    );
    const body = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body as FormData;
    expect(body.get("source_console")).toBe("yamaha_cl");
    expect(body.get("source_model")).toBe("yamaha-cl5");
    expect(body.get("target_model")).toBeTruthy();
  });

  it("clicking Start Over returns to State A", () => {
    render(<UploadFlow />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(input, "files", {
      value: [fileWithName("show.clf")],
      configurable: true,
    });
    fireEvent.change(input);
    expect(screen.getByText(/Source Console/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Start Over/i }));
    expect(screen.queryByText(/Source Console/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Drop your show file/i)).toBeInTheDocument();
  });
});
