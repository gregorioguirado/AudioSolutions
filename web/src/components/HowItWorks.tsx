const STEPS = [
  {
    num: "1",
    title: "Drop",
    icon: "↑",
    desc: "Drop your .cle or .show file. We detect the console.",
  },
  {
    num: "2",
    title: "Translate",
    icon: "⚙",
    desc: "Channels, patch, EQ, dynamics mapped to the target console.",
  },
  {
    num: "3",
    title: "Download",
    icon: "↓",
    desc: "Get the translated show file plus a full PDF report.",
  },
] as const;

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t border-border px-6 py-20">
      <div className="mx-auto max-w-5xl text-center">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">
          How it works
        </p>
        <h2 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">
          Three steps. Thirty seconds.
        </h2>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.num} className="border border-border bg-surface p-6 text-center">
              <p className="text-3xl text-accent">{s.icon}</p>
              <p className="mt-3 text-xs font-extrabold uppercase tracking-wider text-white">
                {s.num}. {s.title}
              </p>
              <p className="mt-2 text-xs leading-relaxed text-muted">{s.desc}</p>
            </div>
          ))}
        </div>

        <a
          href="/translate"
          className="mt-10 inline-block bg-accent px-5 py-2.5 text-xs font-extrabold uppercase tracking-wider text-black no-underline hover:bg-yellow-300"
        >
          Try it free →
        </a>
      </div>
    </section>
  );
}
