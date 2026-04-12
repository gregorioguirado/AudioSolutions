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
}

const STATUS_STYLES = {
  translated: { icon: "✓", color: "text-success" },
  approximated: { icon: "~", color: "text-warning" },
  dropped: { icon: "×", color: "text-error" },
} as const;

function formatParam(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function TranslationPreview({ channelCount, translatedParams, approximatedParams, droppedParams, channels }: Props) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-extrabold uppercase tracking-tight">
          {channelCount} channels translated
        </h2>
      </div>

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
