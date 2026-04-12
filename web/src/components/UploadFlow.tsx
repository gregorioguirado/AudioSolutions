"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import ConsoleSelector from "./ConsoleSelector";
import TranslationPreview from "./TranslationPreview";
import VerifyBanner from "./VerifyBanner";
import SignupWall from "./SignupWall";
import { detectConsole, otherConsole, type ConsoleId } from "@/lib/constants";

type FlowState = "idle" | "uploading" | "preview" | "error";

interface PreviewData {
  translationId: string;
  channelCount: number;
  translatedParams: string[];
  approximatedParams: string[];
  droppedParams: string[];
  authenticated: boolean;
}

export default function UploadFlow() {
  const router = useRouter();
  const [state, setState] = useState<FlowState>("idle");
  const [source, setSource] = useState<ConsoleId>("yamaha_cl");
  const [target, setTarget] = useState<ConsoleId>("digico_sd");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSignupWall, setShowSignupWall] = useState(false);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    const detected = detectConsole(f.name);
    if (detected) {
      setSource(detected);
      setTarget(otherConsole(detected));
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleTranslate = async () => {
    if (!file) return;
    setState("uploading");
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("source_console", source);
    formData.append("target_console", target);

    try {
      const res = await fetch("/api/translate", { method: "POST", body: formData });
      const data = await res.json();

      if (!res.ok) {
        if (res.status === 402) {
          setError("Coming soon — payments launching soon. You've already used your free translation.");
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

  const handleReset = () => {
    setState("idle");
    setFile(null);
    setPreview(null);
    setError(null);
  };

  return (
    <div className="mx-auto max-w-2xl px-6">
      {showSignupWall && (
        <SignupWall onClose={() => setShowSignupWall(false)} onSuccess={handleSignupSuccess} />
      )}

      {state === "idle" && (
        <div className="flex flex-col gap-6">
          <ConsoleSelector source={source} target={target} onSourceChange={setSource} onTargetChange={setTarget} />

          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="relative flex flex-col items-center justify-center border-2 border-dashed border-accent bg-surface p-12 text-center transition-colors hover:bg-accent/10"
          >
            <p className="text-sm font-extrabold uppercase tracking-wider text-accent">Drop your file here</p>
            <p className="mt-1 text-xs text-muted">or click to browse</p>
            <input
              type="file"
              accept=".cle,.clf,.show"
              onChange={handleFileInput}
              className="absolute inset-0 cursor-pointer opacity-0"
            />
          </div>

          {file && (
            <div className="flex items-center justify-between border border-border bg-surface px-4 py-3">
              <p className="text-sm text-white">{file.name}</p>
              <button type="button" onClick={handleTranslate}
                className="bg-accent px-4 py-2 text-xs font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300">
                Translate →
              </button>
            </div>
          )}
        </div>
      )}

      {state === "uploading" && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <p className="text-sm font-extrabold uppercase tracking-wider text-accent">Translating...</p>
          <p className="mt-2 text-xs text-muted">Parsing your show file and mapping to the target console.</p>
        </div>
      )}

      {state === "preview" && preview && (
        <div className="flex flex-col gap-6">
          <VerifyBanner />
          <TranslationPreview
            channelCount={preview.channelCount}
            translatedParams={preview.translatedParams}
            approximatedParams={preview.approximatedParams}
            droppedParams={preview.droppedParams}
            channels={[]}
          />
          <button type="button" onClick={handleDownload}
            className="bg-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300">
            Download translated file
          </button>
          <button type="button" onClick={handleReset} className="text-xs text-muted hover:text-white">
            Translate another file
          </button>
        </div>
      )}

      {state === "error" && (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <p className="text-sm font-bold text-error">{error}</p>
          <button type="button" onClick={handleReset} className="text-xs text-accent hover:underline">Try again</button>
        </div>
      )}
    </div>
  );
}
