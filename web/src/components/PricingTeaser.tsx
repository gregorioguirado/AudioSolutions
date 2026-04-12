const TIERS = [
  { name: "Free", price: "$0", desc: "1 lifetime translation", note: "See what it does", highlighted: false },
  { name: "Credits", price: "$12–90", desc: "1–10 translations", note: "Pay as you go", highlighted: false },
  { name: "Pro", price: "$19/mo", desc: "30 translations/month", note: "For working engineers", highlighted: true },
] as const;

export default function PricingTeaser() {
  return (
    <section id="pricing" className="border-t border-border px-6 py-20">
      <div className="mx-auto max-w-5xl text-center">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">Pricing</p>
        <h2 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">Simple. Honest.</h2>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {TIERS.map((t) => (
            <div key={t.name} className={`border p-6 text-center ${t.highlighted ? "border-accent bg-accent/5" : "border-border bg-surface"}`}>
              <p className="text-xs font-bold uppercase tracking-wider text-muted">{t.name}</p>
              <p className="mt-2 text-2xl font-extrabold text-white">{t.price}</p>
              <p className="mt-1 text-xs text-muted">{t.desc}</p>
              <p className="mt-4 text-[10px] uppercase tracking-wider text-muted">{t.note}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
