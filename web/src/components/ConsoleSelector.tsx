"use client";

import { useState } from "react";
import { CONSOLE_BRANDS, getModelById } from "@/lib/constants";
import DetailCard from "./DetailCard";

interface Props {
  sourceModelId: string | undefined;
  sourceDetected: boolean;
  targetModelId: string | undefined;
  onSourceChange: (modelId: string) => void;
  onTargetChange: (modelId: string) => void;
  disabled?: boolean;
}

export default function ConsoleSelector({
  sourceModelId,
  sourceDetected,
  targetModelId,
  onSourceChange,
  onTargetChange,
  disabled = false,
}: Props) {
  const sourceModel = getModelById(sourceModelId);
  const targetModel = getModelById(targetModelId);

  // Which brand is active on each side. Initialise from the selected model if any.
  const [sourceBrand, setSourceBrand] = useState<string>(sourceModel?.brand ?? "Yamaha");
  const [targetBrand, setTargetBrand] = useState<string>(targetModel?.brand ?? "DiGiCo");

  // Override state — if true, the source side shows the brand-sidebar + search (just like target).
  const [overriding, setOverriding] = useState(false);
  const showSourceOverride = overriding || !sourceDetected;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-[1fr_36px_1fr] items-start gap-0">
        {/* Labels */}
        <p className="col-start-1 row-start-1 text-[10px] font-extrabold uppercase tracking-wider text-muted mb-2">
          Source Console
        </p>
        <p className="col-start-3 row-start-1 text-[10px] font-extrabold uppercase tracking-wider text-muted mb-2">
          Target Console
        </p>

        {/* Source panel */}
        <div className="col-start-1 row-start-2">
          <Panel
            activeBrand={sourceBrand}
            onBrandClick={setSourceBrand}
            selectedModelId={sourceModelId}
            onModelClick={onSourceChange}
            disabled={disabled}
            autoDetected={showSourceOverride ? false : sourceDetected}
            onOverrideClick={() => setOverriding(true)}
          />
        </div>

        {/* Arrow */}
        <div className="col-start-2 row-start-2 flex h-full items-center justify-center text-muted">→</div>

        {/* Target panel */}
        <div className="col-start-3 row-start-2">
          <Panel
            activeBrand={targetBrand}
            onBrandClick={setTargetBrand}
            selectedModelId={targetModelId}
            onModelClick={onTargetChange}
            disabled={disabled}
            autoDetected={false}
          />
        </div>

        {/* Detail cards */}
        <div className="col-start-1 row-start-3 mt-2">
          <DetailCard model={sourceModel} role="source" />
        </div>
        <div className="col-start-3 row-start-3 mt-2">
          <DetailCard model={targetModel} role="target" />
        </div>
      </div>
    </div>
  );
}

// ── Panel (shared by both sides) ───────────────────────────────────────────

interface PanelProps {
  activeBrand: string;
  onBrandClick: (brand: string) => void;
  selectedModelId: string | undefined;
  onModelClick: (modelId: string) => void;
  disabled: boolean;
  autoDetected: boolean;
  onOverrideClick?: () => void;
}

function Panel({
  activeBrand,
  onBrandClick,
  selectedModelId,
  onModelClick,
  disabled,
  autoDetected,
  onOverrideClick,
}: PanelProps) {
  const [query, setQuery] = useState("");
  const brand = CONSOLE_BRANDS.find((b) => b.name === activeBrand) ?? CONSOLE_BRANDS[0];
  const filtered = brand.models.filter((m) =>
    m.model.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="flex border border-border bg-surface">
      {/* Brand sidebar */}
      <div className="w-[130px] shrink-0 border-r border-border bg-[#0d0d0d] p-2">
        <p className="px-1 pb-2 text-[9px] font-extrabold uppercase tracking-widest text-muted">Brand</p>
        {CONSOLE_BRANDS.map((b) => {
          const active = b.name === activeBrand;
          return (
            <button
              key={b.name}
              type="button"
              disabled={disabled}
              onClick={() => onBrandClick(b.name)}
              className={`block w-full text-left px-2 py-2 text-xs whitespace-nowrap disabled:opacity-50 ${
                active ? "bg-accent/10 text-accent font-bold" : "text-muted hover:text-white hover:bg-[#161616]"
              }`}
            >
              {b.name}
            </button>
          );
        })}
      </div>

      {/* Model panel */}
      <div className="flex-1 min-w-0 p-3 flex flex-col gap-2">
        {autoDetected ? (
          <div className="flex items-center gap-2 border border-success/30 bg-success/[0.06] px-3 py-2 text-[11px] text-success">
            <span>✓ Auto-detected</span>
            <button
              type="button"
              onClick={onOverrideClick}
              className="ml-auto text-accent font-bold hover:underline"
            >
              Override
            </button>
          </div>
        ) : (
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Filter ${activeBrand} models…`}
            disabled={disabled}
            className="w-full border border-border bg-bg px-3 py-2 text-xs text-white outline-none focus:border-accent disabled:opacity-50"
          />
        )}

        <div className="flex flex-wrap gap-1.5">
          {filtered.map((m) => {
            const selected = m.id === selectedModelId;
            return (
              <button
                key={m.id}
                type="button"
                disabled={disabled}
                onClick={() => onModelClick(m.id)}
                className={`inline-flex items-center border px-3 py-1.5 text-xs font-semibold disabled:opacity-50 ${
                  selected
                    ? "bg-accent/10 border-accent text-accent"
                    : "border-border bg-surface text-white/80 hover:border-muted"
                }`}
              >
                {m.model}
              </button>
            );
          })}
          {filtered.length === 0 && (
            <p className="text-[11px] text-muted">No models match "{query}".</p>
          )}
        </div>
      </div>
    </div>
  );
}
