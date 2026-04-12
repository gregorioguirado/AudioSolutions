"use client";

import { useState } from "react";

const QUESTIONS = [
  { q: "Is this safe to load into a live console?", a: "Always verify the translated file on the target console before the show. Load it, check the patch list, and spot-check EQ and dynamics on key channels. We generate a full translation report showing exactly what transferred and what didn't." },
  { q: "What consoles are supported?", a: "Yamaha CL/QL and DiGiCo SD/Quantum are supported in both directions. Allen & Heath dLive, Midas PRO, and SSL Live are coming in future updates." },
  { q: "My show has Yamaha Premium Rack plugins. Will those translate?", a: "No. Brand-specific plugins and custom DSP cannot be translated because they have no equivalent on the target console. These are logged in your translation report so you know exactly what was dropped." },
  { q: "Is my file stored anywhere?", a: "Uploaded files are stored temporarily to perform the translation and are automatically deleted within 24 hours. We never share or analyze your show files." },
  { q: "Can I try it before paying?", a: "Yes. Your first translation is completely free — full output file and full report. No credit card required. Just create an account and upload." },
  { q: "Who built this?", a: "Showfier was built by a touring audio engineer who got tired of rebuilding show files at 4am. This tool exists because we needed it ourselves." },
] as const;

export default function FAQ() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section id="faq" className="border-t border-border px-6 py-20">
      <div className="mx-auto max-w-3xl">
        <p className="text-center text-xs font-bold uppercase tracking-[3px] text-accent">FAQ</p>
        <h2 className="mt-3 text-center text-2xl font-extrabold uppercase tracking-tight">Questions</h2>

        <div className="mt-12 flex flex-col gap-2">
          {QUESTIONS.map((item, i) => (
            <div key={i} className="border border-border bg-surface">
              <button
                type="button"
                onClick={() => setOpen(open === i ? null : i)}
                className="flex w-full items-center justify-between px-5 py-4 text-left text-sm font-bold text-white"
              >
                {item.q}
                <span className="ml-4 text-accent">{open === i ? "−" : "+"}</span>
              </button>
              {open === i && (
                <div className="border-t border-border px-5 py-4 text-sm leading-relaxed text-muted">
                  {item.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
