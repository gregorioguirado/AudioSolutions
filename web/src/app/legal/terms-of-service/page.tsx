import fs from "node:fs";
import path from "node:path";
import type { Metadata } from "next";
import { renderMarkdown } from "../_lib/render-markdown";

export const metadata: Metadata = {
  title: "Terms of Service — Showfier",
  description:
    "Showfier Terms of Service: as-is warranty disclaimer, professional-use clause, liability cap, indemnification, and Delaware governing law.",
};

export default function TermsOfServicePage() {
  const filePath = path.join(process.cwd(), "public", "legal", "terms-of-service.md");
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
