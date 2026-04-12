import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import VerifyBanner from "../../src/components/VerifyBanner";

describe("VerifyBanner", () => {
  it("renders the verification warning", () => {
    render(<VerifyBanner />);
    expect(screen.getByText(/verify/i)).toBeInTheDocument();
  });

  it("mentions checking the patch list", () => {
    render(<VerifyBanner />);
    expect(screen.getByText(/patch list/i)).toBeInTheDocument();
  });
});
