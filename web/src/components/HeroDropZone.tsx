"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";

const PREVIEW_CHANNELS = ["KICK", "SNARE", "VOX 1", "GTR L", "BASS DI"];

export default function HeroDropZone() {
  const router = useRouter();

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file) {
        router.push("/translate");
      }
    },
    [router]
  );

  const handleClick = useCallback(() => {
    router.push("/translate");
  }, [router]);

  return (
    <section className="mx-auto grid max-w-5xl grid-cols-1 gap-8 px-6 py-20 md:grid-cols-2 md:items-stretch">
      {/* Left column: pitch + drop zone */}
      <div className="flex flex-col">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">
          ★ Showfier
        </p>
        <h1 className="mt-3 text-3xl font-extrabold uppercase leading-none tracking-tight md:text-4xl">
          Switch console brands
          <br />
          in 30 seconds, not 8 hours.
        </h1>
        <p className="mt-3 text-sm text-muted">
          Upload your show file from one mixing console, download it ready for another. First translation free.
        </p>
        <p className="mt-2 text-xs text-muted">
          Showfier converts show files between Yamaha, DiGiCo, and soon Allen &amp; Heath consoles — so you don&apos;t rebuild from scratch when the venue has the wrong brand.
        </p>
        <button
          type="button"
          onClick={handleClick}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="mt-6 flex flex-1 cursor-pointer flex-col items-center justify-center border-2 border-dashed border-accent bg-surface p-6 text-center transition-colors hover:bg-accent/10"
        >
          <span className="text-sm font-extrabold uppercase tracking-wider text-accent">
            Drop a show file here
          </span>
          <span className="mt-1 text-xs text-muted">.CLF, .CLE, or .show — or click to browse</span>
        </button>
      </div>

      {/* Right column: translation preview */}
      <div className="grid grid-cols-[1fr_auto_1fr] gap-2">
        {/* FROM panel */}
        <div className="flex flex-col border border-border bg-surface p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted">From</p>
          <p className="mt-1 text-sm font-bold">Yamaha CL5</p>
          <div className="mt-3 flex flex-col gap-1">
            {PREVIEW_CHANNELS.map((ch) => (
              <p key={`from-${ch}`} className="text-xs text-white/80">· {ch}</p>
            ))}
          </div>
        </div>

        {/* Arrow */}
        <div className="flex items-center text-xl font-extrabold text-accent">→</div>

        {/* TO panel */}
        <div className="flex flex-col border border-accent bg-surface p-4">
          <p className="text-[10px] uppercase tracking-wider text-accent">To</p>
          <p className="mt-1 text-sm font-bold">DiGiCo SD12</p>
          <div className="mt-3 flex flex-col gap-1">
            {PREVIEW_CHANNELS.map((ch) => (
              <p key={`to-${ch}`} className="text-xs text-success">✓ {ch}</p>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
