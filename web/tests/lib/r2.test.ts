import { describe, expect, it } from "vitest";
import { buildR2Key } from "../../src/lib/r2";

describe("buildR2Key", () => {
  it("builds a key with owner, translation id, and filename", () => {
    const key = buildR2Key("user-123", "tx-456", "translated.show");
    expect(key).toBe("user-123/tx-456/translated.show");
  });
});
