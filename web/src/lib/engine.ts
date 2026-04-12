import type { ConsoleId } from "./constants";

export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024; // 50 MB

export const OUTPUT_FILENAMES: Record<ConsoleId, string> = {
  digico_sd: "translated.show",
  yamaha_cl: "translated.cle",
};

export interface TranslationResult {
  outputBytes: Buffer;
  reportBytes: Buffer;
  channelCount: number;
  translatedParams: string[];
  approximatedParams: string[];
  droppedParams: string[];
}

export async function callEngine(
  file: Buffer,
  filename: string,
  sourceConsole: ConsoleId,
  targetConsole: ConsoleId
): Promise<TranslationResult> {
  const engineUrl = process.env.ENGINE_URL;
  if (!engineUrl) throw new Error("ENGINE_URL not configured");

  const formData = new FormData();
  formData.append("file", new Blob([file]), filename);
  formData.append("source_console", sourceConsole);
  formData.append("target_console", targetConsole);

  const res = await fetch(`${engineUrl}/translate`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(body.detail || `Engine returned ${res.status}`);
  }

  const zipBuffer = Buffer.from(await res.arrayBuffer());

  const JSZip = (await import("jszip")).default;
  const zip = await JSZip.loadAsync(zipBuffer);

  const outputName = OUTPUT_FILENAMES[targetConsole];
  const outputEntry = zip.file(outputName);
  const reportEntry = zip.file("translation_report.pdf");

  if (!outputEntry || !reportEntry) {
    throw new Error("Engine returned invalid bundle — missing files");
  }

  const outputBytes = Buffer.from(await outputEntry.async("arraybuffer"));
  const reportBytes = Buffer.from(await reportEntry.async("arraybuffer"));

  const channelCount = parseInt(res.headers.get("X-Channel-Count") ?? "0", 10);
  const translatedParams = (res.headers.get("X-Translated") ?? "").split(",").filter(Boolean);
  const approximatedParams: string[] = [];
  const droppedParams = (res.headers.get("X-Dropped") ?? "").split(",").filter(Boolean);

  return {
    outputBytes,
    reportBytes,
    channelCount,
    translatedParams,
    approximatedParams,
    droppedParams,
  };
}
