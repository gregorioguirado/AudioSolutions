import type { ConsoleId } from "./constants";

export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024; // 50 MB

// TF, DM7, and RIVAGE are source-only for now — no writer exists yet.
export const OUTPUT_FILENAMES: Record<string, string> = {
  digico_sd: "translated.show",
  yamaha_cl: "translated.cle",
  yamaha_cl_binary: "translated.clf",
  yamaha_ql: "translated.clf",
  ah_dlive: "translated.AHsession",
};

export interface FidelityScore {
  names: number;
  hpf: number;
  eq: number;
  gate: number;
  compressor: number;
  overall: number;
}

export interface TranslationResult {
  outputBytes: Buffer;
  reportBytes: Buffer;
  channelCount: number;
  translatedParams: string[];
  approximatedParams: string[];
  droppedParams: string[];
  parseGatePassed: boolean;
  fidelityScore: FidelityScore | null;
}

export async function callEngine(
  file: Buffer,
  filename: string,
  sourceConsole: ConsoleId,
  targetConsole: ConsoleId,
  userEmail?: string
): Promise<TranslationResult> {
  const engineUrl = process.env.ENGINE_URL;
  if (!engineUrl) throw new Error("ENGINE_URL not configured");

  const formData = new FormData();
  formData.append("file", new Blob([new Uint8Array(file)]), filename);
  formData.append("source_console", sourceConsole);
  formData.append("target_console", targetConsole);
  if (userEmail) formData.append("user_email", userEmail);

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

  const outputName = OUTPUT_FILENAMES[targetConsole] ?? "translated.bin";
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

  const parseGatePassed = (res.headers.get("X-Parse-Gate-Passed") ?? "true") !== "false";

  const parseFidelityHeader = (name: string): number =>
    parseFloat(res.headers.get(name) ?? "100");

  const hasFidelity = res.headers.has("X-Fidelity-Overall");
  const fidelityScore: FidelityScore | null = hasFidelity
    ? {
        names: parseFidelityHeader("X-Fidelity-Names"),
        hpf: parseFidelityHeader("X-Fidelity-HPF"),
        eq: parseFidelityHeader("X-Fidelity-EQ"),
        gate: parseFidelityHeader("X-Fidelity-Gate"),
        compressor: parseFidelityHeader("X-Fidelity-Compressor"),
        overall: parseFidelityHeader("X-Fidelity-Overall"),
      }
    : null;

  return {
    outputBytes,
    reportBytes,
    channelCount,
    translatedParams,
    approximatedParams,
    droppedParams,
    parseGatePassed,
    fidelityScore,
  };
}
