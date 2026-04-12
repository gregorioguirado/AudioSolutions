import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getPresignedUrl } from "@/lib/r2";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { searchParams } = new URL(request.url);
  const fileType = searchParams.get("type");

  if (!fileType || !["output", "report", "source"].includes(fileType)) {
    return NextResponse.json({ error: "Invalid file type" }, { status: 400 });
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data: translation } = await supabase
    .from("translations")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (!translation) {
    return NextResponse.json({ error: "Translation not found" }, { status: 404 });
  }

  const keyMap: Record<string, string | null> = {
    output: translation.output_r2_key,
    report: translation.report_r2_key,
    source: translation.source_r2_key,
  };

  const r2Key = keyMap[fileType];
  if (!r2Key) {
    return NextResponse.json({ error: "File not available" }, { status: 404 });
  }

  const bucketMap: Record<string, string> = {
    output: process.env.R2_BUCKET_OUTPUTS!,
    report: process.env.R2_BUCKET_REPORTS!,
    source: process.env.R2_BUCKET_SOURCES!,
  };

  const url = await getPresignedUrl(bucketMap[fileType], r2Key);
  return NextResponse.redirect(url);
}
