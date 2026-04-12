import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import UploadFlow from "@/components/UploadFlow";
import TranslationHistory from "@/components/TranslationHistory";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: translations } = await supabase
    .from("translations")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(10);

  return (
    <main className="py-12">
      <div className="mx-auto max-w-3xl px-6">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">★ Showfier</p>
        <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">Dashboard</h1>

        <div className="mt-8">
          <h2 className="text-sm font-bold uppercase tracking-wider text-muted">New translation</h2>
          <div className="mt-4"><UploadFlow /></div>
        </div>

        <div className="mt-12">
          <h2 className="text-sm font-bold uppercase tracking-wider text-muted">Recent translations</h2>
          <div className="mt-4"><TranslationHistory translations={translations ?? []} /></div>
        </div>
      </div>
    </main>
  );
}
