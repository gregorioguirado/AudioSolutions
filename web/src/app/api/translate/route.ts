import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createClient } from "@/lib/supabase/server";
import { callEngine, MAX_UPLOAD_BYTES, OUTPUT_FILENAMES } from "@/lib/engine";
import { uploadToR2, buildR2Key } from "@/lib/r2";
import type { ConsoleId } from "@/lib/constants";
import { CONSOLES } from "@/lib/constants";

const VALID_CONSOLES = CONSOLES.map((c) => c.id);

export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get("file") as File | null;
  const sourceConsole = formData.get("source_console") as string | null;
  const targetConsole = formData.get("target_console") as string | null;
  const sourceModel = formData.get("source_model") as string | null;
  const targetModel = formData.get("target_model") as string | null;

  if (!file || !sourceConsole || !targetConsole) {
    return NextResponse.json({ error: "Missing file, source_console, or target_console" }, { status: 400 });
  }

  if (!VALID_CONSOLES.includes(sourceConsole as ConsoleId)) {
    return NextResponse.json({ error: `Unsupported source console: ${sourceConsole}` }, { status: 400 });
  }

  if (!VALID_CONSOLES.includes(targetConsole as ConsoleId)) {
    return NextResponse.json({ error: `Unsupported target console: ${targetConsole}` }, { status: 400 });
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    return NextResponse.json({ error: "File too large, 50MB max" }, { status: 413 });
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  const adminEmails = (process.env.ADMIN_EMAILS ?? "").split(",").map(e => e.trim().toLowerCase());
  const isAdmin = user ? adminEmails.includes(user.email?.toLowerCase() ?? "") : false;

  if (user) {

    if (!isAdmin) {
      const { data: profile } = await supabase
        .from("profiles")
        .select("free_used")
        .eq("id", user.id)
        .single();

      if (profile?.free_used) {
        return NextResponse.json(
          { error: "payments_required", message: "Coming soon — payments launching soon." },
          { status: 402 }
        );
      }
    }
  }

  const fileBuffer = Buffer.from(await file.arrayBuffer());
  let result;
  try {
    result = await callEngine(fileBuffer, file.name, sourceConsole as ConsoleId, targetConsole as ConsoleId, user?.email ?? undefined);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Translation failed";
    const status = message.includes("Unsupported") ? 400 : 500;
    return NextResponse.json({ error: message }, { status });
  }

  if (!result.parseGatePassed) {
    return NextResponse.json(
      { error: "Translation produced an unreadable output file. Please try again or contact support." },
      { status: 422 }
    );
  }

  const translationId = crypto.randomUUID();
  const ownerId = user?.id ?? crypto.randomUUID();

  const sourceKey = buildR2Key(ownerId, translationId, file.name);
  const outputKey = buildR2Key(ownerId, translationId, OUTPUT_FILENAMES[targetConsole as ConsoleId]);
  const reportKey = buildR2Key(ownerId, translationId, "translation_report.pdf");

  try {
    await Promise.all([
      uploadToR2(process.env.R2_BUCKET_SOURCES!, sourceKey, fileBuffer, "application/octet-stream"),
      uploadToR2(process.env.R2_BUCKET_OUTPUTS!, outputKey, result.outputBytes, "application/octet-stream"),
      uploadToR2(process.env.R2_BUCKET_REPORTS!, reportKey, result.reportBytes, "application/pdf"),
    ]);
  } catch {
    return NextResponse.json({ error: "Failed to store translation files. Please try again." }, { status: 500 });
  }

  if (user) {
    await supabase.from("translations").insert({
      id: translationId,
      user_id: user.id,
      source_console: sourceConsole,
      target_console: targetConsole,
      source_model: sourceModel,
      target_model: targetModel,
      channel_names: [],
      source_filename: file.name,
      source_r2_key: sourceKey,
      output_r2_key: outputKey,
      report_r2_key: reportKey,
      channel_count: result.channelCount,
      translated_params: result.translatedParams,
      approximated_params: result.approximatedParams,
      dropped_params: result.droppedParams,
      status: "complete",
    });

    if (!isAdmin) {
      await supabase.from("profiles").update({ free_used: true }).eq("id", user.id);
    }

    return NextResponse.json({
      translationId,
      channelCount: result.channelCount,
      translatedParams: result.translatedParams,
      approximatedParams: result.approximatedParams,
      droppedParams: result.droppedParams,
      fidelityScore: result.fidelityScore,
      authenticated: true,
    });
  } else {
    const sessionToken = crypto.randomUUID();
    const cookieStore = await cookies();
    cookieStore.set("preview_token", sessionToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 3600,
      path: "/",
    });

    await supabase.from("anonymous_previews").insert({
      id: translationId,
      session_token: sessionToken,
      source_model: sourceModel,
      target_model: targetModel,
      channel_names: [],
      source_r2_key: sourceKey,
      output_r2_key: outputKey,
      report_r2_key: reportKey,
      channel_count: result.channelCount,
      translated_params: result.translatedParams,
      approximated_params: result.approximatedParams,
      dropped_params: result.droppedParams,
    });

    return NextResponse.json({
      translationId,
      channelCount: result.channelCount,
      translatedParams: result.translatedParams,
      approximatedParams: result.approximatedParams,
      droppedParams: result.droppedParams,
      fidelityScore: result.fidelityScore,
      authenticated: false,
    });
  }
}
