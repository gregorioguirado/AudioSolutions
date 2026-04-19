"use client";

import { useState } from "react";
import VerifyBeforeDoorsModal from "./VerifyBeforeDoorsModal";

interface DownloadLink {
  href: string;
  label: string;
  /** "primary" gets the filled-accent button, "secondary" gets the outline. */
  variant?: "primary" | "secondary";
}

interface Props {
  links: DownloadLink[];
}

/**
 * Client wrapper that renders one Download button per link and routes every
 * click through {@link VerifyBeforeDoorsModal}. Used from server components
 * (e.g. the translation detail page) that can't own modal state directly.
 */
export default function DownloadButtonsWithVerify({ links }: Props) {
  const [pendingHref, setPendingHref] = useState<string | null>(null);
  const [pendingLabel, setPendingLabel] = useState<string>("Download");

  const handleConfirm = () => {
    if (pendingHref) {
      window.location.href = pendingHref;
    }
    setPendingHref(null);
  };

  return (
    <div className="flex flex-col gap-3">
      {links.map((link) => {
        const variant = link.variant ?? "primary";
        const baseClasses =
          "flex items-center justify-center px-6 py-3 text-sm font-extrabold uppercase tracking-wider transition-opacity";
        const variantClasses =
          variant === "primary"
            ? "bg-accent text-black hover:bg-yellow-300"
            : "border border-accent text-accent hover:bg-accent/10";

        return (
          <button
            key={link.href}
            type="button"
            onClick={() => {
              setPendingHref(link.href);
              setPendingLabel(link.label);
            }}
            className={`${baseClasses} ${variantClasses}`}
          >
            {link.label}
          </button>
        );
      })}

      <VerifyBeforeDoorsModal
        open={pendingHref !== null}
        onCancel={() => setPendingHref(null)}
        onConfirm={handleConfirm}
        downloadLabel={pendingLabel}
      />
    </div>
  );
}
