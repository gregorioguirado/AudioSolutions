import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import UploadFlow from "@/components/UploadFlow";
import TranslationHistory, { type Translation } from "@/components/TranslationHistory";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data } = await supabase
    .from("translations")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(20);

  const translations: Translation[] = (data ?? []).map((row) => ({
    id: row.id,
    source_console: row.source_console,
    target_console: row.target_console,
    source_model: row.source_model,
    target_model: row.target_model,
    source_filename: row.source_filename,
    channel_count: row.channel_count,
    translated_params: row.translated_params ?? [],
    approximated_params: row.approximated_params ?? [],
    dropped_params: row.dropped_params ?? [],
    channel_names: row.channel_names ?? [],
    status: row.status,
    created_at: row.created_at,
  }));

  return (
    <main className="py-12">
      <div className="mx-auto max-w-5xl px-6">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">★ Showfier</p>
        <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">Dashboard</h1>

        <div className="mt-8">
          <h2 className="text-[10px] font-extrabold uppercase tracking-wider text-muted">
            New Translation
          </h2>
          <div className="mt-3"><UploadFlow /></div>
        </div>

        <div className="mt-12">
          <h2 className="text-[10px] font-extrabold uppercase tracking-wider text-muted">
            Recent Translations
          </h2>
          <div className="mt-3">
            <TranslationHistory translations={translations} />
          </div>
        </div>
      </div>
    </main>
  );
}
