import Link from "next/link";
import { consoleLabel } from "@/lib/constants";

interface Translation {
  id: string;
  source_console: string;
  target_console: string;
  source_filename: string;
  channel_count: number;
  status: string;
  created_at: string;
}

interface Props {
  translations: Translation[];
}

export default function TranslationHistory({ translations }: Props) {
  if (translations.length === 0) {
    return (
      <div className="border border-border bg-surface px-6 py-10 text-center">
        <p className="text-sm text-muted">No translations yet.</p>
        <p className="mt-1 text-xs text-muted">Upload a show file above to get started.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {translations.map((t) => (
        <Link key={t.id} href={`/translations/${t.id}`}
          className="flex items-center justify-between border border-border bg-surface px-4 py-3 no-underline transition-colors hover:border-accent/30">
          <div>
            <p className="text-sm font-bold text-white">{t.source_filename}</p>
            <p className="mt-0.5 text-xs text-muted">
              {consoleLabel(t.source_console)} → {consoleLabel(t.target_console)} · {t.channel_count} channels
            </p>
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-wider text-muted">{new Date(t.created_at).toLocaleDateString()}</p>
            <p className={`text-xs font-bold ${t.status === "complete" ? "text-success" : "text-warning"}`}>{t.status}</p>
          </div>
        </Link>
      ))}
    </div>
  );
}
