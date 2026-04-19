"use client";

import { useEffect, useId, useRef, useState } from "react";

interface Props {
  /** Controls whether the modal is rendered. */
  open: boolean;
  /** Called when the user dismisses the modal (Cancel button or Escape). */
  onCancel: () => void;
  /** Called when the user confirms (clicks Download after acknowledging). */
  onConfirm: () => void;
  /**
   * Label used inside the modal's confirm button. Tailored per call-site so
   * the user knows exactly which file the download will produce
   * (e.g. "Download translated file" vs "Download translation report (PDF)").
   */
  downloadLabel: string;
}

/**
 * Required acknowledgement modal shown before any translated show file
 * is downloaded.
 *
 * The modal supersedes the inline checkbox pattern. It enforces the
 * §14 Translation Accuracy Disclaimer at a single, unmissable choke point
 * so the user has to actively confirm "I will verify on the target console
 * before any live performance" before the download is triggered.
 */
export default function VerifyBeforeDoorsModal({
  open,
  onCancel,
  onConfirm,
  downloadLabel,
}: Props) {
  const [acknowledged, setAcknowledged] = useState(false);
  const titleId = useId();
  const descId = useId();
  const checkboxId = useId();
  const cancelButtonRef = useRef<HTMLButtonElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  // Reset acknowledgement every time the modal is reopened so a previous
  // session never carries over.
  useEffect(() => {
    if (open) {
      setAcknowledged(false);
    }
  }, [open]);

  // Escape closes the modal. Listen on document so the handler fires even
  // when focus is somewhere unusual.
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onCancel]);

  // Move focus into the dialog when it opens — Cancel is the safest default
  // focus target since it never triggers a download.
  useEffect(() => {
    if (open) {
      cancelButtonRef.current?.focus();
    }
  }, [open]);

  // Simple focus trap: keep Tab/Shift+Tab cycling inside the dialog.
  useEffect(() => {
    if (!open) return;
    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const root = dialogRef.current;
      if (!root) return;
      const focusable = root.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleTab);
    return () => document.removeEventListener("keydown", handleTab);
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        className="mx-4 w-full max-w-md border border-warning/40 bg-bg p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-xs font-bold uppercase tracking-[3px] text-warning">
          ⚠ Acknowledgement required
        </p>
        <h2
          id={titleId}
          className="mt-2 text-xl font-extrabold uppercase tracking-tight text-white"
        >
          Verify before doors
        </h2>

        <p id={descId} className="mt-3 text-sm leading-relaxed text-muted">
          Showfier translations are automated approximations. Some parameters may be wrong,
          missing, or dropped. You must verify the translation on the target console before
          any live performance.
        </p>

        <label
          htmlFor={checkboxId}
          className="mt-5 flex cursor-pointer items-start gap-3 border border-warning/30 bg-warning/[0.06] p-4"
        >
          <input
            id={checkboxId}
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer accent-warning"
          />
          <span className="text-sm leading-relaxed text-white">
            I will verify on the target console before any live performance.
          </span>
        </label>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row-reverse">
          <button
            type="button"
            disabled={!acknowledged}
            onClick={() => {
              if (!acknowledged) return;
              onConfirm();
            }}
            className="flex-1 bg-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {downloadLabel}
          </button>
          <button
            ref={cancelButtonRef}
            type="button"
            onClick={onCancel}
            className="flex-1 border border-border px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-muted hover:border-white hover:text-white"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
