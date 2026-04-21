import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getPresignedUrl } from "@/lib/r2";
import path from "path";

const TARGET_EXT: Record<string, string> = {
  digico_sd: ".show",
  yamaha_cl: ".cle",
  yamaha_cl_binary: ".CLF",
  yamaha_ql: ".CLF",
  yamaha_tf: ".tff",
  yamaha_dm7: ".dm7f",
  yamaha_rivage: ".RIVAGEPM",
};

function deriveFilename(
  fileType: string,
  sourceFilename: string,
  targetConsole: string
): string {
  const stem = path.basename(sourceFilename, path.extname(sourceFilename));
  if (fileType === "output") {
    const ext = TARGET_EXT[targetConsole] ?? ".out";
    return `${stem}_showfier${ext}`;
  }
  if (fileType === "report") {
    return `${stem}_showfier_report.pdf`;
  }
  return path.basename(sourceFilename);
}

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

  const downloadFilename = deriveFilename(
    fileType,
    translation.source_filename ?? "translation",
    translation.target_console ?? ""
  );

  // Fetch from R2 server-side and proxy with proper Content-Disposition so the
  // browser downloads the file without navigating away from the app.
  const presignedUrl = await getPresignedUrl(bucketMap[fileType], r2Key, 60);
  const r2Response = await fetch(presignedUrl);

  if (!r2Response.ok) {
    return NextResponse.json({ error: "Failed to retrieve file" }, { status: 502 });
  }

  const contentType =
    fileType === "report"
      ? "application/pdf"
      : "application/octet-stream";

  return new NextResponse(r2Response.body, {
    status: 200,
    headers: {
      "Content-Type": contentType,
      "Content-Disposition": `attachment; filename="${downloadFilename}"`,
      "Cache-Control": "private, no-store",
    },
  });
}
