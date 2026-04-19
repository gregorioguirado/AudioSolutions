import { redirect, notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { consoleLabel } from "@/lib/constants";
import TranslationPreview from "@/components/TranslationPreview";
import VerifyBanner from "@/components/VerifyBanner";
import Timecode from "@/components/Timecode";
import DownloadButtonsWithVerify from "@/components/DownloadButtonsWithVerify";

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
        <div className="mt-1 flex items-center gap-3 text-sm text-muted">
          <span>
            {consoleLabel(translation.source_console)} → {consoleLabel(translation.target_console)}
          </span>
          <Timecode iso={translation.created_at} />
        </div>

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

        <div className="mt-8">
          <DownloadButtonsWithVerify
            links={[
              {
                href: `/api/download/${translation.id}?type=output`,
                label: "Download translated file",
                variant: "primary",
              },
              {
                href: `/api/download/${translation.id}?type=report`,
                label: "Download translation report (PDF)",
                variant: "secondary",
              },
            ]}
          />
        </div>
      </div>
    </main>
  );
}
