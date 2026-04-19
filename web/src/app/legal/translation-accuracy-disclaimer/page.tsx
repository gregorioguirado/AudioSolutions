import fs from "node:fs";
import path from "node:path";
import type { Metadata } from "next";
import { renderMarkdown } from "../_lib/render-markdown";

export const metadata: Metadata = {
  title: "Translation Accuracy Disclaimer — Showfier",
  description:
    "The translation accuracy disclaimer all Showfier users acknowledge before downloading a translated show file.",
};

export default function TranslationAccuracyDisclaimerPage() {
  const filePath = path.join(
    process.cwd(),
    "public",
    "legal",
    "translation-accuracy-disclaimer.md",
  );
  const md = fs.readFileSync(filePath, "utf8");
  const html = renderMarkdown(md);

  return (
    <main className="py-12">
      <div className="mx-auto max-w-3xl px-6">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">★ Showfier</p>
        <article
          className="mt-6"
          // eslint-disable-next-line react/no-danger -- markdown source is a static, in-repo file
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </div>
    </main>
  );
}
