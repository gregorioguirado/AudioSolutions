import { describe, expect, it } from "vitest";
import { detectConsole, CONSOLES, otherConsole } from "../../src/lib/constants";

describe("detectConsole", () => {
  it("detects .cle as yamaha_cl", () => {
    expect(detectConsole("my_show.cle")).toBe("yamaha_cl");
  });

  it("detects .CLE as yamaha_cl (case-insensitive)", () => {
    expect(detectConsole("my_show.CLE")).toBe("yamaha_cl");
  });

  it("detects .show as digico_sd", () => {
    expect(detectConsole("festival.show")).toBe("digico_sd");
  });

  it("returns null for unknown extensions", () => {
    expect(detectConsole("notes.txt")).toBeNull();
  });

  it("returns null for no extension", () => {
    expect(detectConsole("README")).toBeNull();
  });
});

describe("otherConsole", () => {
  it("returns digico_sd for yamaha_cl", () => {
    expect(otherConsole("yamaha_cl")).toBe("digico_sd");
  });

  it("returns yamaha_cl for digico_sd", () => {
    expect(otherConsole("digico_sd")).toBe("yamaha_cl");
  });
});

describe("CONSOLES", () => {
  it("has exactly two entries", () => {
    expect(CONSOLES).toHaveLength(2);
  });

  it("each entry has id and label", () => {
    for (const c of CONSOLES) {
      expect(c).toHaveProperty("id");
      expect(c).toHaveProperty("label");
    }
  });
});
