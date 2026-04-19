import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import VerifyBeforeDoorsModal from "@/components/VerifyBeforeDoorsModal";

describe("VerifyBeforeDoorsModal", () => {
  it("renders title, body, checkbox, Cancel and Download buttons when open", () => {
    render(
      <VerifyBeforeDoorsModal
        open={true}
        onCancel={() => {}}
        onConfirm={() => {}}
        downloadLabel="Download translated file"
      />,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/verify before doors/i)).toBeInTheDocument();

    expect(
      screen.getByRole("checkbox", {
        name: /verify on the target console before any live performance/i,
      }),
    ).toBeInTheDocument();

    expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^download translated file$/i }),
    ).toBeInTheDocument();
  });

  it("does not render anything when open is false", () => {
    render(
      <VerifyBeforeDoorsModal
        open={false}
        onCancel={() => {}}
        onConfirm={() => {}}
        downloadLabel="Download translated file"
      />,
    );

    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("disables the Download button until the checkbox is checked", () => {
    render(
      <VerifyBeforeDoorsModal
        open={true}
        onCancel={() => {}}
        onConfirm={() => {}}
        downloadLabel="Download translated file"
      />,
    );

    const downloadBtn = screen.getByRole("button", {
      name: /^download translated file$/i,
    });
    expect(downloadBtn).toBeDisabled();

    const checkbox = screen.getByRole("checkbox", {
      name: /verify on the target console before any live performance/i,
    });
    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();
    expect(downloadBtn).toBeEnabled();
  });

  it("calls onConfirm when Download is clicked after acknowledgement", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <VerifyBeforeDoorsModal
        open={true}
        onCancel={onCancel}
        onConfirm={onConfirm}
        downloadLabel="Download translated file"
      />,
    );

    const checkbox = screen.getByRole("checkbox", {
      name: /verify on the target console before any live performance/i,
    });
    fireEvent.click(checkbox);

    fireEvent.click(
      screen.getByRole("button", { name: /^download translated file$/i }),
    );

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("calls onCancel and does NOT call onConfirm when Cancel is clicked", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <VerifyBeforeDoorsModal
        open={true}
        onCancel={onCancel}
        onConfirm={onConfirm}
        downloadLabel="Download translated file"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("closes (calls onCancel) when Escape is pressed", () => {
    const onCancel = vi.fn();
    const onConfirm = vi.fn();
    render(
      <VerifyBeforeDoorsModal
        open={true}
        onCancel={onCancel}
        onConfirm={onConfirm}
        downloadLabel="Download translated file"
      />,
    );

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("has dialog ARIA attributes for accessibility", () => {
    render(
      <VerifyBeforeDoorsModal
        open={true}
        onCancel={() => {}}
        onConfirm={() => {}}
        downloadLabel="Download translated file"
      />,
    );

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAttribute("aria-labelledby");
    expect(dialog).toHaveAttribute("aria-describedby");
  });
});
