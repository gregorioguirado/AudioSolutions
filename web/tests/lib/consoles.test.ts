import { describe, it, expect } from "vitest";
import {
  CONSOLE_BRANDS,
  getModelById,
  detectModelFromFilename,
  brandIdForModel,
  consoleLabel,
  detectConsole,
} from "@/lib/constants";

describe("console catalog", () => {
  it("exposes all supported brands in order", () => {
    expect(CONSOLE_BRANDS.map((b) => b.name)).toEqual([
      "Yamaha",
      "DiGiCo",
    ]);
  });

  it("each model has required fields", () => {
    for (const brand of CONSOLE_BRANDS) {
      for (const model of brand.models) {
        expect(model.id).toBeTruthy();
        expect(model.brand).toBe(brand.name);
        expect(model.series).toBeTruthy();
        expect(model.model).toBeTruthy();
        expect(typeof model.maxChannels).toBe("number");
        expect(typeof model.mixBuses).toBe("number");
        expect(model.fileFormat.startsWith(".")).toBe(true);
      }
    }
  });

  it("getModelById returns the model", () => {
    const cl5 = getModelById("yamaha-cl5");
    expect(cl5?.model).toBe("CL5");
    expect(cl5?.maxChannels).toBe(72);
  });

  it("getModelById returns undefined for unknown", () => {
    expect(getModelById("nope")).toBeUndefined();
  });

  it("detectModelFromFilename picks a reasonable default per extension", () => {
    expect(detectModelFromFilename("show.clf")?.id).toBe("yamaha-cl5");
    expect(detectModelFromFilename("show.cle")?.id).toBe("yamaha-cl5");
    expect(detectModelFromFilename("show.show")?.id).toBe("digico-sd12");
    expect(detectModelFromFilename("weird.xyz")).toBeNull();
  });

  it("brandIdForModel maps to legacy engine brand id", () => {
    expect(brandIdForModel("yamaha-cl5")).toBe("yamaha_cl");
    expect(brandIdForModel("yamaha-ql5")).toBe("yamaha_cl");
    expect(brandIdForModel("digico-sd12")).toBe("digico_sd");
    expect(brandIdForModel("digico-quantum-338")).toBe("digico_sd");
  });

  it("detectConsole preserves legacy behaviour for back-compat", () => {
    expect(detectConsole("show.clf")).toBe("yamaha_cl");
    expect(detectConsole("show.show")).toBe("digico_sd");
    expect(detectConsole("weird.xyz")).toBeNull();
  });

  it("consoleLabel resolves brand-id labels", () => {
    expect(consoleLabel("yamaha_cl")).toBe("Yamaha CL/QL");
    expect(consoleLabel("digico_sd")).toBe("DiGiCo SD/Quantum");
  });
});
