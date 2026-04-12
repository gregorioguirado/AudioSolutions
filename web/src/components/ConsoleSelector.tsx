import { CONSOLES, type ConsoleId } from "@/lib/constants";

interface Props {
  source: ConsoleId;
  target: ConsoleId;
  onSourceChange: (id: ConsoleId) => void;
  onTargetChange: (id: ConsoleId) => void;
  disabled?: boolean;
}

export default function ConsoleSelector({ source, target, onSourceChange, onTargetChange, disabled = false }: Props) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1">
        <label htmlFor="source-console" className="text-[10px] font-bold uppercase tracking-wider text-muted">From</label>
        <select
          id="source-console"
          value={source}
          onChange={(e) => onSourceChange(e.target.value as ConsoleId)}
          disabled={disabled}
          className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent disabled:opacity-50"
        >
          {CONSOLES.map((c) => (
            <option key={c.id} value={c.id}>{c.label}</option>
          ))}
        </select>
      </div>
      <span className="mt-5 text-lg font-extrabold text-accent">→</span>
      <div className="flex-1">
        <label htmlFor="target-console" className="text-[10px] font-bold uppercase tracking-wider text-muted">To</label>
        <select
          id="target-console"
          value={target}
          onChange={(e) => onTargetChange(e.target.value as ConsoleId)}
          disabled={disabled}
          className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent disabled:opacity-50"
        >
          {CONSOLES.map((c) => (
            <option key={c.id} value={c.id}>{c.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
