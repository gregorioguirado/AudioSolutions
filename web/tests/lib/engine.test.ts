import { describe, expect, it } from "vitest";
import { OUTPUT_FILENAMES, MAX_UPLOAD_BYTES } from "../../src/lib/engine";

describe("engine constants", () => {
  it("maps digico_sd to .show extension", () => {
    expect(OUTPUT_FILENAMES["digico_sd"]).toBe("translated.show");
  });

  it("maps yamaha_cl to .cle extension", () => {
    expect(OUTPUT_FILENAMES["yamaha_cl"]).toBe("translated.cle");
  });

  it("sets max upload to 50MB", () => {
    expect(MAX_UPLOAD_BYTES).toBe(50 * 1024 * 1024);
  });
});
