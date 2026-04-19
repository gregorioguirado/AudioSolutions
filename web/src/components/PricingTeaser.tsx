type Tier = {
  name: string;
  price: string;
  priceSub?: string;
  desc: string;
  note: string;
  highlighted: boolean;
};

const TIERS: readonly Tier[] = [
  {
    name: "Free",
    price: "$0",
    desc: "1 lifetime translation",
    note: "Try it",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$19/mo",
    priceSub: "or $149/yr",
    desc: "Unlimited translations",
    note: "For working engineers",
    highlighted: true,
  },
  {
    name: "Team",
    price: "Contact us",
    desc: "Multi-seat, custom",
    note: "For rental companies",
    highlighted: false,
  },
] as const;

export default function PricingTeaser() {
  return (
    <section id="pricing" className="border-t border-border px-6 py-20">
      <div className="mx-auto max-w-5xl text-center">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">Pricing</p>
        <h2 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">Simple. Honest.</h2>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {TIERS.map((t) => (
            <div
              key={t.name}
              className={`border p-6 text-center ${t.highlighted ? "border-accent bg-accent/5" : "border-border bg-surface"}`}
            >
              <p className="text-xs font-bold uppercase tracking-wider text-muted">{t.name}</p>
              <p className="mt-2 text-2xl font-extrabold text-white">{t.price}</p>
              {t.priceSub && (
                <p className="mt-1 text-[11px] text-muted">{t.priceSub}</p>
              )}
              <p className="mt-1 text-xs text-muted">{t.desc}</p>
              <p className="mt-4 text-[10px] uppercase tracking-wider text-muted">{t.note}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
