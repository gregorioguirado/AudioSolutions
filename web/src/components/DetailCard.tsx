import type { ConsoleModel } from "@/lib/constants";

interface Props {
  model: ConsoleModel | undefined;
  role: "source" | "target";
}

export default function DetailCard({ model, role }: Props) {
  if (!model) {
    return (
      <div className="border border-border bg-surface px-4 py-6 text-center">
        <p className="text-xs text-muted">
          {role === "source" ? "Select a source console" : "Select a target console"}
        </p>
      </div>
    );
  }

  return (
    <div className="border border-border bg-surface px-4 py-4">
      <div>
        <h4 className="text-sm font-extrabold text-white">{model.model}</h4>
        <p className="mt-0.5 text-[10px] font-bold uppercase tracking-wider text-muted">
          {model.series} · {role === "source" ? "Source" : "Target"}
        </p>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-wider text-muted">File format</span>
        <span className="text-xs font-bold text-white">{model.fileFormat}</span>
      </div>

      <p className="mt-3 border-t border-border pt-2 text-[10px] font-extrabold uppercase tracking-wider text-success">
        {role === "source" ? "✓ Detected from file" : "✓ Supported"}
      </p>
    </div>
  );
}
