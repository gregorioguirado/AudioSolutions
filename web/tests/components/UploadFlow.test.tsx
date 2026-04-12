import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import UploadFlow from "../../src/components/UploadFlow";

describe("UploadFlow", () => {
  it("renders the drop zone in initial state", () => {
    render(<UploadFlow />);
    expect(screen.getByText(/drop your file here/i)).toBeInTheDocument();
  });

  it("renders console selectors", () => {
    render(<UploadFlow />);
    expect(screen.getByLabelText(/from/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/to/i)).toBeInTheDocument();
  });
});
