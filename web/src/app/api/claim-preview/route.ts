import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createClient } from "@/lib/supabase/server";

export async function POST() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const cookieStore = await cookies();
  const previewToken = cookieStore.get("preview_token")?.value;

  if (!previewToken) {
    return NextResponse.json({ error: "No preview to claim" }, { status: 404 });
  }

  const { data: preview } = await supabase
    .from("anonymous_previews")
    .select("*")
    .eq("session_token", previewToken)
    .single();

  if (!preview) {
    return NextResponse.json({ error: "Preview not found or expired" }, { status: 404 });
  }

  const { error: insertError } = await supabase.from("translations").insert({
    id: preview.id,
    user_id: user.id,
    source_console: "unknown",
    target_console: "unknown",
    source_filename: "uploaded_file",
    source_r2_key: preview.source_r2_key,
    output_r2_key: preview.output_r2_key,
    report_r2_key: preview.report_r2_key,
    channel_count: preview.channel_count ?? 0,
    translated_params: preview.translated_params ?? [],
    approximated_params: preview.approximated_params ?? [],
    dropped_params: preview.dropped_params ?? [],
    status: "complete",
  });

  if (insertError) {
    return NextResponse.json({ error: "Failed to claim preview" }, { status: 500 });
  }

  await supabase.from("profiles").update({ free_used: true }).eq("id", user.id);
  await supabase.from("anonymous_previews").delete().eq("session_token", previewToken);
  cookieStore.delete("preview_token");

  return NextResponse.json({ translationId: preview.id });
}
