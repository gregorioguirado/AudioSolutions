"use client";

import { useState } from "react";
import { consoleLabel } from "@/lib/constants";
import Timecode from "./Timecode";
import ReportPane from "./ReportPane";

export interface Translation {
  id: string;
  source_console: string;
  target_console: string;
  source_model?: string | null;
  target_model?: string | null;
  source_filename: string;
  channel_count: number;
  translated_params: string[];
  approximated_params: string[];
  dropped_params: string[];
  channel_names: string[];
  status: string;
  created_at: string;
}

interface Props {
  translations: Translation[];
}

export default function TranslationHistory({ translations }: Props) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const active = translations.find((t) => t.id === activeId) ?? null;

  if (translations.length === 0) {
    return (
      <div className="border border-border bg-surface px-6 py-10 text-center">
        <p className="text-sm text-muted">No translations yet.</p>
        <p className="mt-1 text-xs text-muted">Upload a show file above to get started.</p>
      </div>
    );
  }

  return (
    <div className="flex border border-border bg-surface">
      <div className="flex-1 min-w-0">
        {translations.map((t) => (
          <Row
            key={t.id}
            t={t}
            active={t.id === activeId}
            onClick={() => setActiveId(t.id === activeId ? null : t.id)}
          />
        ))}
      </div>
      {active && (
        <ReportPane translation={active} onClose={() => setActiveId(null)} />
      )}
    </div>
  );
}

function Row({
  t,
  active,
  onClick,
}: {
  t: Translation;
  active: boolean;
  onClick: () => void;
}) {
  const tx = t.translated_params.length;
  const ap = t.approximated_params.length;
  const dr = t.dropped_params.length;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-4 border-b border-border px-4 py-3 text-left last:border-b-0 hover:bg-[#131313] ${
        active ? "bg-[#131313] border-l-2 border-l-accent pl-[14px]" : ""
      }`}
    >
      <span className="text-lg shrink-0">📄</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-bold text-white truncate">{t.source_filename}</p>
        <p className="mt-0.5 text-[11px] text-muted truncate">
          {consoleLabel(t.source_console)} → {consoleLabel(t.target_console)}
        </p>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {tx > 0 && (
            <span className="border border-success/30 bg-success/[0.06] px-2 py-0.5 text-[10px] font-bold text-success">
              ✓ {tx} translated
            </span>
          )}
          {ap > 0 && (
            <span className="border border-warning/30 bg-warning/[0.06] px-2 py-0.5 text-[10px] font-bold text-warning">
              ~ {ap} approx
            </span>
          )}
          {dr > 0 && (
            <span className="border border-error/30 bg-error/[0.06] px-2 py-0.5 text-[10px] font-bold text-error">
              × {dr} dropped
            </span>
          )}
        </div>
      </div>
      <span className="text-[11px] text-muted whitespace-nowrap shrink-0">
        {t.channel_count} ch
      </span>
      <Timecode iso={t.created_at} />
      <span className="text-[10px] font-extrabold uppercase tracking-wider text-success shrink-0">
        {t.status === "complete" ? "Done" : t.status}
      </span>
    </button>
  );
}
