import { redirect, notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { consoleLabel } from "@/lib/constants";
import TranslationPreview from "@/components/TranslationPreview";
import VerifyBanner from "@/components/VerifyBanner";

export default async function TranslationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: translation } = await supabase
    .from("translations")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (!translation) {
    notFound();
  }

  return (
    <main className="py-12">
      <div className="mx-auto max-w-2xl px-6">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">★ Showfier</p>
        <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">{translation.source_filename}</h1>
        <p className="mt-1 text-sm text-muted">
          {consoleLabel(translation.source_console)} → {consoleLabel(translation.target_console)} · {new Date(translation.created_at).toLocaleDateString()}
        </p>

        <div className="mt-6"><VerifyBanner /></div>

        <div className="mt-6">
          <TranslationPreview
            channelCount={translation.channel_count}
            translatedParams={translation.translated_params}
            approximatedParams={translation.approximated_params}
            droppedParams={translation.dropped_params}
            channels={[]}
          />
        </div>

        <div className="mt-8 flex flex-col gap-3">
          <a href={`/api/download/${translation.id}?type=output`}
            className="flex items-center justify-center bg-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-black no-underline hover:bg-yellow-300">
            Download translated file
          </a>
          <a href={`/api/download/${translation.id}?type=report`}
            className="flex items-center justify-center border border-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-accent no-underline hover:bg-accent/10">
            Download translation report (PDF)
          </a>
        </div>
      </div>
    </main>
  );
}
