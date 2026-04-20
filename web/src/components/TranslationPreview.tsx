import type { FidelityScore } from "@/lib/engine";

interface Channel {
  name: string;
  status: "translated" | "approximated" | "dropped";
}

interface Props {
  channelCount: number;
  translatedParams: string[];
  approximatedParams: string[];
  droppedParams: string[];
  channels: Channel[];
  fidelityScore?: FidelityScore | null;
}

const STATUS_STYLES = {
  translated: { icon: "✓", color: "text-success" },
  approximated: { icon: "~", color: "text-warning" },
  dropped: { icon: "×", color: "text-error" },
} as const;

function formatParam(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function FidelityRow({ label, value, bold = false }: { label: string; value: number; bold?: boolean }) {
  const color = value >= 95 ? "bg-success" : value >= 80 ? "bg-warning" : "bg-error";
  const textColor = value >= 95 ? "text-success" : value >= 80 ? "text-warning" : "text-error";
  return (
    <div className="flex items-center gap-3">
      <span className={`w-14 text-[11px] ${bold ? "font-extrabold text-white" : "text-muted"}`}>{label}</span>
      <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${value}%` }} />
      </div>
      <span className={`w-12 text-right text-[11px] tabular-nums ${bold ? "font-extrabold " + textColor : textColor}`}>
        {value.toFixed(1)}%
      </span>
    </div>
  );
}

export default function TranslationPreview({ channelCount, translatedParams, approximatedParams, droppedParams, channels, fidelityScore }: Props) {
  const overall = fidelityScore?.overall;
  const verdict =
    overall === undefined ? null :
    overall >= 95 ? { label: "HIGH FIDELITY — all parameters survived", cls: "text-success" } :
    overall >= 80 ? { label: "MEDIUM FIDELITY — minor loss, review below", cls: "text-warning" } :
                    { label: "LOW FIDELITY — significant parameter loss", cls: "text-error" };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-extrabold uppercase tracking-tight">
          {channelCount} channels translated
        </h2>
      </div>

      {overall !== undefined && overall < 80 && (
        <div className="border border-error/30 bg-error/[0.06] p-4">
          <p className="text-[10px] font-extrabold uppercase tracking-[3px] text-error">⚠ Low-fidelity translation</p>
          <p className="mt-2 text-sm text-white leading-relaxed">
            Not all parameters survived the round-trip. Review the fidelity breakdown below before loading on console.
          </p>
        </div>
      )}

      {fidelityScore != null && (
        <div className="border border-border bg-surface p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted mb-3">Fidelity</p>
          <div className="flex items-baseline gap-3 mb-3">
            <span className="text-3xl font-extrabold tabular-nums text-white">{fidelityScore.overall.toFixed(1)}%</span>
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted">Overall</span>
          </div>
          {verdict && (
            <p className={`text-xs font-extrabold uppercase tracking-wider mb-4 ${verdict.cls}`}>{verdict.label}</p>
          )}
          <div className="flex flex-col gap-2">
            {[
              { label: "Names", value: fidelityScore.names },
              { label: "HPF", value: fidelityScore.hpf },
              { label: "EQ", value: fidelityScore.eq },
              { label: "Gate", value: fidelityScore.gate },
              { label: "Comp", value: fidelityScore.compressor },
            ].map(({ label, value }) => (
              <FidelityRow key={label} label={label} value={value} />
            ))}
          </div>
        </div>
      )}

      {channels.length > 0 && (
        <div className="border border-border bg-surface p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted">Channel list</p>
          <div className="mt-3 flex flex-col gap-1">
            {channels.map((ch) => {
              const style = STATUS_STYLES[ch.status];
              return (
                <div key={ch.name} className="flex items-center gap-2 text-sm">
                  <span className={`font-bold ${style.color}`}>{style.icon}</span>
                  <span className="text-white">{ch.name}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="border border-border bg-surface p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-success">✓ Translated</p>
          <ul className="mt-2 flex flex-col gap-1">
            {translatedParams.map((p) => (
              <li key={p} className="text-xs text-white/80">{formatParam(p)}</li>
            ))}
          </ul>
        </div>
        <div className="border border-border bg-surface p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-warning">~ Approximated</p>
          <ul className="mt-2 flex flex-col gap-1">
            {approximatedParams.length === 0 ? (
              <li className="text-xs text-muted">None</li>
            ) : (
              approximatedParams.map((p) => (
                <li key={p} className="text-xs text-white/80">{formatParam(p)}</li>
              ))
            )}
          </ul>
        </div>
        <div className="border border-border bg-surface p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-error">× Dropped</p>
          <ul className="mt-2 flex flex-col gap-1">
            {droppedParams.length === 0 ? (
              <li className="text-xs text-muted">None</li>
            ) : (
              droppedParams.map((p) => (
                <li key={p} className="text-xs text-white/80">{formatParam(p)}</li>
              ))
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
