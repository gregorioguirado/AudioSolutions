import { consoleLabel } from "@/lib/constants";

interface Translation {
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
  translation: Translation;
  onClose: () => void;
}

function formatParam(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ReportPane({ translation: t, onClose }: Props) {
  const route = `${consoleLabel(t.source_console)} → ${consoleLabel(t.target_console)}`;
  // Channel names have their own dedicated section below, so avoid listing
  // "channel_names" again inside the Translated params list.
  const translatedParams = t.translated_params.filter((p) => p !== "channel_names");
  const tx = translatedParams.length;
  const ap = t.approximated_params.length;
  const dr = t.dropped_params.length;

  return (
    <aside className="w-[300px] shrink-0 border-l border-border bg-[#0d0d0d] p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-extrabold text-white break-words">{t.source_filename}</h4>
          <p className="mt-1 text-[10px] font-bold uppercase tracking-wider text-muted">
            {route} · {t.channel_count} ch
          </p>
        </div>
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="text-muted hover:text-white"
        >
          ✕
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {tx > 0 && (
          <span className="border border-success/30 bg-success/[0.06] px-2 py-0.5 text-[10px] font-bold text-success">
            ✓ {tx}
          </span>
        )}
        {ap > 0 && (
          <span className="border border-warning/30 bg-warning/[0.06] px-2 py-0.5 text-[10px] font-bold text-warning">
            ~ {ap}
          </span>
        )}
        {dr > 0 && (
          <span className="border border-error/30 bg-error/[0.06] px-2 py-0.5 text-[10px] font-bold text-error">
            × {dr}
          </span>
        )}
      </div>

      <Section title="✓ Translated" color="text-success">
        {translatedParams.map((p) => (
          <ParamItem key={p}>{formatParam(p)}</ParamItem>
        ))}
      </Section>

      {ap > 0 && (
        <Section title="~ Approximated" color="text-warning">
          {t.approximated_params.map((p) => (
            <ParamItem key={p}>{formatParam(p)}</ParamItem>
          ))}
        </Section>
      )}

      {dr > 0 && (
        <Section title="× Dropped" color="text-error">
          {t.dropped_params.map((p) => (
            <ParamItem key={p}>{formatParam(p)}</ParamItem>
          ))}
        </Section>
      )}

      <Section title="Channel Names" color="text-muted">
        {t.channel_names.length === 0 ? (
          <p className="text-[11px] text-muted italic">Channel names not stored for this translation.</p>
        ) : (
          <div className="grid grid-cols-2 gap-1">
            {t.channel_names.slice(0, 24).map((n, i) => (
              <div
                key={`${n}-${i}`}
                className="border border-border bg-surface px-2 py-1 text-[11px] text-white/80 overflow-hidden text-ellipsis whitespace-nowrap"
              >
                {n}
              </div>
            ))}
            {t.channel_names.length > 24 && (
              <p className="col-span-2 text-[10px] text-muted">+{t.channel_names.length - 24} more…</p>
            )}
          </div>
        )}
      </Section>

      <a
        href={`/api/download/${t.id}?type=output`}
        className="mt-4 block w-full bg-accent px-4 py-2.5 text-center text-xs font-extrabold uppercase tracking-wider text-black no-underline hover:bg-yellow-300"
      >
        Download .show
      </a>
    </aside>
  );
}

function Section({
  title,
  color,
  children,
}: {
  title: string;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-4">
      <p className={`text-[10px] font-extrabold uppercase tracking-wider ${color}`}>{title}</p>
      <div className="mt-1 flex flex-col gap-0.5">{children}</div>
    </div>
  );
}

function ParamItem({ children }: { children: React.ReactNode }) {
  return (
    <p className="border-b border-border/50 py-1 text-[11px] text-white/70 last:border-b-0">
      {children}
    </p>
  );
}
