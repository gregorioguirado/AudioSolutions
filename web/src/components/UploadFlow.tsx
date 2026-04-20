"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import ConsoleSelector from "./ConsoleSelector";
import TranslationPreview from "./TranslationPreview";
import VerifyBanner from "./VerifyBanner";
import SignupWall from "./SignupWall";
import DownloadButtonsWithVerify from "./DownloadButtonsWithVerify";
import {
  detectModelFromFilename,
  getModelById,
  brandIdForModel,
  type ConsoleModel,
} from "@/lib/constants";
import type { FidelityScore } from "@/lib/engine";

type FlowState = "idle" | "configuring" | "uploading" | "preview" | "error";

interface PreviewData {
  translationId: string;
  channelCount: number;
  translatedParams: string[];
  approximatedParams: string[];
  droppedParams: string[];
  fidelityScore: FidelityScore | null;
  authenticated: boolean;
}

const DEFAULT_TARGET_FOR_SOURCE_BRAND: Record<string, string> = {
  Yamaha: "digico-sd12",
  DiGiCo: "yamaha-cl5",
};

export default function UploadFlow() {
  const router = useRouter();
  const [state, setState] = useState<FlowState>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [sourceModelId, setSourceModelId] = useState<string | undefined>();
  const [sourceDetected, setSourceDetected] = useState(false);
  const [targetModelId, setTargetModelId] = useState<string | undefined>();
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSignupWall, setShowSignupWall] = useState(false);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    const detected = detectModelFromFilename(f.name);
    if (detected) {
      setSourceModelId(detected.id);
      setSourceDetected(true);
      setTargetModelId(DEFAULT_TARGET_FOR_SOURCE_BRAND[detected.brand] ?? "digico-sd12");
    } else {
      setSourceModelId(undefined);
      setSourceDetected(false);
      setTargetModelId(undefined);
    }
    setState("configuring");
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  const handleReset = () => {
    setState("idle");
    setFile(null);
    setSourceModelId(undefined);
    setSourceDetected(false);
    setTargetModelId(undefined);
    setPreview(null);
    setError(null);
  };

  const sourceModel: ConsoleModel | undefined = getModelById(sourceModelId);
  const targetModel: ConsoleModel | undefined = getModelById(targetModelId);
  const canTranslate = state === "configuring" && !!file && !!sourceModel && !!targetModel;

  const handleTranslate = async () => {
    if (!canTranslate) return;
    setState("uploading");
    setError(null);

    const formData = new FormData();
    formData.append("file", file!);
    formData.append("source_console", brandIdForModel(sourceModelId!)!);
    formData.append("target_console", brandIdForModel(targetModelId!)!);
    formData.append("source_model", sourceModelId!);
    formData.append("target_model", targetModelId!);

    try {
      const res = await fetch("/api/translate", { method: "POST", body: formData });
      const data = await res.json();

      if (!res.ok) {
        if (res.status === 402) {
          setError(
            "Coming soon — payments launching soon. You've already used your free translation.",
          );
          setState("error");
          return;
        }
        throw new Error(data.error || "Translation failed");
      }

      setPreview(data);
      setState("preview");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong";
      setError(message);
      setState("error");
    }
  };

  const handleDownload = () => {
    if (!preview) return;
    if (!preview.authenticated) {
      setShowSignupWall(true);
      return;
    }
    router.push(`/translations/${preview.translationId}`);
  };

  const handleSignupSuccess = async () => {
    setShowSignupWall(false);
    const res = await fetch("/api/claim-preview", { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      router.push(`/translations/${data.translationId}`);
      router.refresh();
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {showSignupWall && (
        <SignupWall onClose={() => setShowSignupWall(false)} onSuccess={handleSignupSuccess} />
      )}

      {/* ── State A: idle ── */}
      {state === "idle" && (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="relative flex flex-col items-center justify-center border-2 border-dashed border-border bg-surface p-12 text-center transition-colors hover:border-accent/40 hover:bg-accent/[0.03]"
        >
          <p className="text-sm font-extrabold uppercase tracking-wider text-white">
            Drop your show file here
          </p>
          <p className="mt-1 text-xs text-muted">We&apos;ll detect your console automatically</p>
          <p className="mt-3 text-[10px] text-muted">.clf · .cle · .show · .tff · .dm7f · .rivagepm</p>
          <div className="mt-4 inline-block bg-accent px-5 py-2 text-xs font-extrabold uppercase tracking-wider text-black">
            Choose File
          </div>
          <input
            type="file"
            accept=".cle,.clf,.show,.tff,.dm7f,.rivagepm,.RIVAGEPM"
            onChange={handleFileInput}
            className="absolute inset-0 cursor-pointer opacity-0"
          />
        </div>
      )}

      {/* ── State B: configuring ── */}
      {state === "configuring" && file && (
        <>
          <div className="flex items-center gap-3 border border-success/30 bg-success/[0.06] px-4 py-3">
            <span className="text-xl">📄</span>
            <div>
              <p className="text-sm font-bold text-white">{file.name}</p>
              {sourceDetected && sourceModel && (
                <p className="mt-0.5 text-xs text-success">
                  ✓ Detected: {sourceModel.brand} {sourceModel.model}
                </p>
              )}
              {!sourceDetected && (
                <p className="mt-0.5 text-xs text-warning">
                  ⚠ Could not auto-detect — pick the source console below
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={handleReset}
              className="ml-auto text-xs font-extrabold uppercase tracking-wider text-muted hover:text-white"
            >
              Start Over
            </button>
          </div>

          <ConsoleSelector
            sourceModelId={sourceModelId}
            sourceDetected={sourceDetected}
            targetModelId={targetModelId}
            onSourceChange={(id) => {
              setSourceModelId(id);
              setSourceDetected(false);
            }}
            onTargetChange={setTargetModelId}
          />

          <button
            type="button"
            onClick={handleTranslate}
            disabled={!canTranslate}
            className="w-full bg-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300 disabled:opacity-40"
          >
            Translate →
          </button>
        </>
      )}

      {/* ── State: uploading ── */}
      {state === "uploading" && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <p className="text-sm font-extrabold uppercase tracking-wider text-accent">Translating...</p>
          <p className="mt-2 text-xs text-muted">
            Parsing your show file and mapping to the target console.
          </p>
        </div>
      )}

      {/* ── State: preview ── */}
      {state === "preview" && preview && (
        <div className="flex flex-col gap-6">
          <VerifyBanner />
          <TranslationPreview
            channelCount={preview.channelCount}
            translatedParams={preview.translatedParams}
            approximatedParams={preview.approximatedParams}
            droppedParams={preview.droppedParams}
            channels={[]}
            fidelityScore={preview.fidelityScore}
          />
          {preview.authenticated ? (
            <div className="flex flex-col gap-3">
              <DownloadButtonsWithVerify
                links={[
                  {
                    href: `/api/download/${preview.translationId}?type=output`,
                    label: "Download translated file",
                    variant: "primary",
                  },
                  {
                    href: `/api/download/${preview.translationId}?type=report`,
                    label: "Download translation report (PDF)",
                    variant: "secondary",
                  },
                ]}
              />
              <button
                type="button"
                onClick={() => router.push(`/translations/${preview.translationId}`)}
                className="text-xs text-muted hover:text-white"
              >
                View full details
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleDownload}
              className="bg-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300"
            >
              Download translated file
            </button>
          )}
          <button type="button" onClick={handleReset} className="text-xs text-muted hover:text-white">
            Translate another file
          </button>
        </div>
      )}

      {/* ── State: error ── */}
      {state === "error" && (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <p className="text-sm font-bold text-error">{error}</p>
          <button
            type="button"
            onClick={handleReset}
            className="text-xs text-accent hover:underline"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
