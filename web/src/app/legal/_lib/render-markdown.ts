/**
 * Tiny inline markdown -> HTML renderer for the /legal pages.
 *
 * We deliberately do NOT pull in a markdown library here — these documents are
 * authored in-house, the formatting needs are minimal, and avoiding a runtime
 * dep keeps the bundle slim. Supports: # headings, **bold**, *italic*,
 * `code`, > blockquote, --- hr, [text](href) links, and - / * bullet lists.
 */

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInline(text: string): string {
  let out = escapeHtml(text);
  // Inline code first so the contents are not re-processed.
  out = out.replace(/`([^`]+)`/g, '<code class="rounded bg-surface px-1 py-0.5 text-xs">$1</code>');
  // Bold then italic. Bold uses ** ** ; italic uses single * * (after bold).
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-bold text-white">$1</strong>');
  out = out.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  // Links: [text](href)
  out = out.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" class="text-accent hover:underline">$1</a>',
  );
  return out;
}

export function renderMarkdown(md: string): string {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const html: string[] = [];
  let i = 0;

  const flushList = (items: string[]) => {
    if (items.length === 0) return;
    html.push('<ul class="ml-6 list-disc space-y-1 text-sm leading-relaxed text-white/80">');
    for (const item of items) html.push(`<li>${renderInline(item)}</li>`);
    html.push("</ul>");
  };

  while (i < lines.length) {
    const line = lines[i];

    // Blank line
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Horizontal rule
    if (/^---+\s*$/.test(line)) {
      html.push('<hr class="my-8 border-border" />');
      i++;
      continue;
    }

    // Headings
    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      const level = heading[1].length;
      const content = renderInline(heading[2]);
      const sizes: Record<number, string> = {
        1: "mt-0 mb-6 text-3xl font-extrabold uppercase tracking-tight text-white",
        2: "mt-10 mb-3 text-xl font-extrabold uppercase tracking-tight text-white",
        3: "mt-8 mb-2 text-base font-extrabold uppercase tracking-wider text-accent",
        4: "mt-6 mb-2 text-sm font-bold uppercase tracking-wider text-white",
        5: "mt-4 mb-2 text-sm font-bold text-white",
        6: "mt-4 mb-2 text-sm font-bold text-muted",
      };
      html.push(`<h${level} class="${sizes[level]}">${content}</h${level}>`);
      i++;
      continue;
    }

    // Blockquote (consume consecutive > lines)
    if (line.startsWith(">")) {
      const buf: string[] = [];
      while (i < lines.length && lines[i].startsWith(">")) {
        buf.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      html.push(
        `<blockquote class="my-6 border-l-4 border-warning bg-warning/[0.06] px-5 py-4 text-sm leading-relaxed text-white">${renderInline(buf.join(" "))}</blockquote>`,
      );
      continue;
    }

    // Bullet list (consume consecutive - or * lines)
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
        i++;
      }
      flushList(items);
      continue;
    }

    // Paragraph (gather consecutive non-special lines)
    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !/^---+\s*$/.test(lines[i]) &&
      !/^#{1,6}\s+/.test(lines[i]) &&
      !lines[i].startsWith(">") &&
      !/^\s*[-*]\s+/.test(lines[i])
    ) {
      para.push(lines[i]);
      i++;
    }
    if (para.length > 0) {
      html.push(
        `<p class="my-3 text-sm leading-relaxed text-white/80">${renderInline(para.join(" "))}</p>`,
      );
    }
  }

  return html.join("\n");
}
