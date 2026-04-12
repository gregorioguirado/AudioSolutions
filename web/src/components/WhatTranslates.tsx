const TRANSLATES = [
  "Channel names",
  "Input patch",
  "HPF frequency",
  "EQ bands",
  "Gate / compressor",
  "Mix bus routing",
  "VCA assignments",
];

const DOESNT = [
  "Brand-specific plugins (Yamaha Premium Rack, etc.)",
  "Custom DSP processing",
  "Scene / snapshot data",
];

export default function WhatTranslates() {
  return (
    <section className="border-t border-border px-6 py-20">
      <div className="mx-auto grid max-w-5xl grid-cols-1 gap-10 md:grid-cols-2">
        <div>
          <h3 className="text-sm font-extrabold uppercase tracking-wider text-success">
            ✓ What translates
          </h3>
          <ul className="mt-4 flex flex-col gap-2">
            {TRANSLATES.map((item) => (
              <li key={item} className="text-sm text-white/80">✓ {item}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-extrabold uppercase tracking-wider text-error">
            × What doesn&apos;t
          </h3>
          <ul className="mt-4 flex flex-col gap-2">
            {DOESNT.map((item) => (
              <li key={item} className="text-sm text-white/60">× {item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
