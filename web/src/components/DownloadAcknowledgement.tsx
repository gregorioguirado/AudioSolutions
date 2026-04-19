"use client";

import { useId, useState } from "react";

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
 * Wraps one or more download links behind a required acknowledgement checkbox.
 *
 * The Showfier ToS and the §14 Translation Accuracy Disclaimer both require
 * that the user explicitly acknowledge the verify-before-doors warning before
 * a translated show file is delivered. This component enforces that gate on
 * the client: until the checkbox is ticked, the links render as disabled
 * buttons that cannot navigate.
 */
export default function DownloadAcknowledgement({ links }: Props) {
  const [acknowledged, setAcknowledged] = useState(false);
  const checkboxId = useId();

  return (
    <div className="flex flex-col gap-4">
      <label
        htmlFor={checkboxId}
        className="flex cursor-pointer items-start gap-3 border border-warning/30 bg-warning/[0.06] p-4"
      >
        <input
          id={checkboxId}
          type="checkbox"
          checked={acknowledged}
          onChange={(e) => setAcknowledged(e.target.checked)}
          className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer accent-warning"
          aria-describedby={`${checkboxId}-desc`}
        />
        <span id={`${checkboxId}-desc`} className="text-sm leading-relaxed text-white">
          I understand translations must be verified on the target console before any live
          performance.
        </span>
      </label>

      <div className="flex flex-col gap-3">
        {links.map((link) => {
          const variant = link.variant ?? "primary";
          const baseClasses =
            "flex items-center justify-center px-6 py-3 text-sm font-extrabold uppercase tracking-wider no-underline transition-opacity";
          const variantClasses =
            variant === "primary"
              ? "bg-accent text-black hover:bg-yellow-300"
              : "border border-accent text-accent hover:bg-accent/10";

          if (!acknowledged) {
            return (
              <button
                key={link.href}
                type="button"
                disabled
                aria-disabled="true"
                className={`${baseClasses} ${variantClasses} cursor-not-allowed opacity-40`}
              >
                {link.label}
              </button>
            );
          }

          return (
            <a key={link.href} href={link.href} className={`${baseClasses} ${variantClasses}`}>
              {link.label}
            </a>
          );
        })}
      </div>
    </div>
  );
}
