# Dashboard UX Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Showfier dashboard with a brand→model console selector, a file-first upload flow, an inline translation report pane, and timezone-aware timestamps — all on the existing Showfier brand system.

**Architecture:** Frontend-only Next.js 14 App Router changes plus one Supabase migration. No engine backend changes. New foundational components (Timecode, DetailCard, CompatBar, ReportPane) feed into rewrites of ConsoleSelector, UploadFlow, TranslationHistory, and the dashboard page. Vitest + Testing Library for unit tests (setup already in place).

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript, Tailwind CSS (custom theme in `web/tailwind.config.ts`), Supabase (Postgres + SSR auth), Vitest, date-fns (to be added).

**Source spec:** [`docs/superpowers/specs/2026-04-17-dashboard-ux-improvements-design.md`](../specs/2026-04-17-dashboard-ux-improvements-design.md)

---

## Notes for the executor

- All file paths are relative to the repo root (`c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions/`).
- Run commands from **inside `web/`** unless otherwise noted.
- Tests live in `web/tests/components/` (not colocated). Follow that existing convention.
- The Showfier brand tokens are defined in `web/tailwind.config.ts`: `bg`, `surface`, `border`, `accent`, `success`, `warning`, `error`, `muted`. Use them, don't inline hex values.
- Channel names are not yet returned by the translation engine. This plan persists a `channel_names text[]` column with graceful empty-state handling; the engine-side change is a future plan.
- The backend engine still only understands the two legacy console IDs (`yamaha_cl`, `digico_sd`). The new design stores **both** the brand-level engine ID (existing `source_console` / `target_console` columns) **and** the specific model ID (new `source_model` / `target_model` columns). Translation routing uses the brand-level ID.

---

## Task 1: Add date-fns dependency

**Files:**
- Modify: `web/package.json` (dependencies)
- Modify: `web/package-lock.json` (regenerated)

- [ ] **Step 1: Install date-fns**

From the `web/` directory:

```bash
cd web && npm install date-fns
```

Expected: `date-fns` appears in `package.json` under `dependencies` with a version string like `^4.x.x`.

- [ ] **Step 2: Verify import works**

Create a scratch file `web/scratch-datefns.mjs`:

```js
import { formatDistanceToNow } from "date-fns";
console.log(formatDistanceToNow(new Date(Date.now() - 2 * 60 * 60 * 1000), { addSuffix: true }));
```

Run:

```bash
cd web && node scratch-datefns.mjs
```

Expected output: `about 2 hours ago` (or similar). Then delete the scratch file:

```bash
rm web/scratch-datefns.mjs
```

- [ ] **Step 3: Commit**

```bash
git add web/package.json web/package-lock.json
git commit -m "chore(web): add date-fns for timecode formatting"
```

---

## Task 2: Expand console catalog

Replace the flat `CONSOLES` array with a brand → model hierarchy while preserving backward-compatible exports used by the engine and existing code.

**Files:**
- Modify: `web/src/lib/constants.ts`
- Create: `web/tests/lib/consoles.test.ts`

- [ ] **Step 1: Write failing test**

Create `web/tests/lib/consoles.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import {
  CONSOLE_BRANDS,
  getModelById,
  detectModelFromFilename,
  brandIdForModel,
  consoleLabel,
  detectConsole,
} from "@/lib/constants";

describe("console catalog", () => {
  it("exposes all supported brands in order", () => {
    expect(CONSOLE_BRANDS.map((b) => b.name)).toEqual([
      "Yamaha",
      "DiGiCo",
    ]);
  });

  it("each model has required fields", () => {
    for (const brand of CONSOLE_BRANDS) {
      for (const model of brand.models) {
        expect(model.id).toBeTruthy();
        expect(model.brand).toBe(brand.name);
        expect(model.series).toBeTruthy();
        expect(model.model).toBeTruthy();
        expect(typeof model.maxChannels).toBe("number");
        expect(typeof model.mixBuses).toBe("number");
        expect(model.fileFormat.startsWith(".")).toBe(true);
      }
    }
  });

  it("getModelById returns the model", () => {
    const cl5 = getModelById("yamaha-cl5");
    expect(cl5?.model).toBe("CL5");
    expect(cl5?.maxChannels).toBe(72);
  });

  it("getModelById returns undefined for unknown", () => {
    expect(getModelById("nope")).toBeUndefined();
  });

  it("detectModelFromFilename picks a reasonable default per extension", () => {
    expect(detectModelFromFilename("show.clf")?.id).toBe("yamaha-cl5");
    expect(detectModelFromFilename("show.cle")?.id).toBe("yamaha-cl5");
    expect(detectModelFromFilename("show.show")?.id).toBe("digico-sd12");
    expect(detectModelFromFilename("weird.xyz")).toBeNull();
  });

  it("brandIdForModel maps to legacy engine brand id", () => {
    expect(brandIdForModel("yamaha-cl5")).toBe("yamaha_cl");
    expect(brandIdForModel("yamaha-ql5")).toBe("yamaha_cl");
    expect(brandIdForModel("digico-sd12")).toBe("digico_sd");
    expect(brandIdForModel("digico-quantum-338")).toBe("digico_sd");
  });

  it("detectConsole preserves legacy behaviour for back-compat", () => {
    expect(detectConsole("show.clf")).toBe("yamaha_cl");
    expect(detectConsole("show.show")).toBe("digico_sd");
    expect(detectConsole("weird.xyz")).toBeNull();
  });

  it("consoleLabel resolves brand-id labels", () => {
    expect(consoleLabel("yamaha_cl")).toBe("Yamaha CL/QL");
    expect(consoleLabel("digico_sd")).toBe("DiGiCo SD/Quantum");
  });
});
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd web && npm run test -- tests/lib/consoles.test.ts
```

Expected: the test file cannot resolve `CONSOLE_BRANDS`, `getModelById`, `detectModelFromFilename`, or `brandIdForModel` — tests fail.

- [ ] **Step 3: Replace `web/src/lib/constants.ts`**

```ts
// Legacy engine-brand IDs — the translation engine still understands only these.
export const CONSOLES = [
  { id: "yamaha_cl", label: "Yamaha CL/QL" },
  { id: "digico_sd", label: "DiGiCo SD/Quantum" },
] as const;

export type ConsoleId = (typeof CONSOLES)[number]["id"];

// New per-model catalogue used by the UI.
export type ConsoleModel = {
  id: string;          // stable slug, e.g. "yamaha-cl5"
  brand: string;       // human-readable brand, e.g. "Yamaha"
  brandId: ConsoleId;  // maps to the engine's brand-level ID
  series: string;      // e.g. "CL Series"
  model: string;       // e.g. "CL5"
  maxChannels: number;
  mixBuses: number;
  fileFormat: string;  // e.g. ".clf"
  supported: boolean;  // whether the engine currently supports it
};

export type ConsoleBrand = {
  name: string;
  models: ConsoleModel[];
};

export const CONSOLE_BRANDS: ConsoleBrand[] = [
  {
    name: "Yamaha",
    models: [
      { id: "yamaha-cl5",   brand: "Yamaha", brandId: "yamaha_cl", series: "CL Series", model: "CL5",         maxChannels: 72,  mixBuses: 24, fileFormat: ".clf", supported: true  },
      { id: "yamaha-cl3",   brand: "Yamaha", brandId: "yamaha_cl", series: "CL Series", model: "CL3",         maxChannels: 64,  mixBuses: 24, fileFormat: ".clf", supported: true  },
      { id: "yamaha-cl1",   brand: "Yamaha", brandId: "yamaha_cl", series: "CL Series", model: "CL1",         maxChannels: 48,  mixBuses: 24, fileFormat: ".clf", supported: true  },
      { id: "yamaha-ql5",   brand: "Yamaha", brandId: "yamaha_cl", series: "QL Series", model: "QL5",         maxChannels: 64,  mixBuses: 16, fileFormat: ".cle", supported: true  },
      { id: "yamaha-ql1",   brand: "Yamaha", brandId: "yamaha_cl", series: "QL Series", model: "QL1",         maxChannels: 32,  mixBuses: 16, fileFormat: ".cle", supported: true  },
      { id: "yamaha-tf5",   brand: "Yamaha", brandId: "yamaha_cl", series: "TF Series", model: "TF5",         maxChannels: 32,  mixBuses: 20, fileFormat: ".cle", supported: false },
      { id: "yamaha-tf3",   brand: "Yamaha", brandId: "yamaha_cl", series: "TF Series", model: "TF3",         maxChannels: 32,  mixBuses: 20, fileFormat: ".cle", supported: false },
      { id: "yamaha-tf1",   brand: "Yamaha", brandId: "yamaha_cl", series: "TF Series", model: "TF1",         maxChannels: 32,  mixBuses: 20, fileFormat: ".cle", supported: false },
      { id: "yamaha-dm7",   brand: "Yamaha", brandId: "yamaha_cl", series: "DM Series", model: "DM7",         maxChannels: 144, mixBuses: 72, fileFormat: ".cle", supported: false },
      { id: "yamaha-rivage-pm10", brand: "Yamaha", brandId: "yamaha_cl", series: "RIVAGE", model: "RIVAGE PM10", maxChannels: 216, mixBuses: 72, fileFormat: ".cle", supported: false },
    ],
  },
  {
    name: "DiGiCo",
    models: [
      { id: "digico-sd5",          brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD5",          maxChannels: 168, mixBuses: 56, fileFormat: ".show", supported: true  },
      { id: "digico-sd7",          brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD7",          maxChannels: 144, mixBuses: 56, fileFormat: ".show", supported: true  },
      { id: "digico-sd9",          brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD9",          maxChannels: 48,  mixBuses: 24, fileFormat: ".show", supported: true  },
      { id: "digico-sd10",         brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD10",         maxChannels: 56,  mixBuses: 24, fileFormat: ".show", supported: true  },
      { id: "digico-sd11",         brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD11",         maxChannels: 48,  mixBuses: 24, fileFormat: ".show", supported: true  },
      { id: "digico-sd12",         brand: "DiGiCo", brandId: "digico_sd", series: "SD Series", model: "SD12",         maxChannels: 96,  mixBuses: 48, fileFormat: ".show", supported: true  },
      { id: "digico-quantum-338",  brand: "DiGiCo", brandId: "digico_sd", series: "Quantum",   model: "Quantum 338",  maxChannels: 338, mixBuses: 96, fileFormat: ".show", supported: true  },
      { id: "digico-quantum-7",    brand: "DiGiCo", brandId: "digico_sd", series: "Quantum",   model: "Quantum 7",    maxChannels: 144, mixBuses: 48, fileFormat: ".show", supported: true  },
      { id: "digico-quantum-225",  brand: "DiGiCo", brandId: "digico_sd", series: "Quantum",   model: "Quantum 225",  maxChannels: 225, mixBuses: 64, fileFormat: ".show", supported: true  },
      { id: "digico-t-series",     brand: "DiGiCo", brandId: "digico_sd", series: "T-Series",  model: "T-Series",     maxChannels: 48,  mixBuses: 24, fileFormat: ".show", supported: true  },
    ],
  },
];

// Other brands (Allen & Heath, Midas, SSL Live) are intentionally out of this list
// until the engine supports them. The data model (ConsoleBrand/ConsoleModel) is ready
// to accept them — just add a new entry and flip `supported: true`.

const MODEL_INDEX: Record<string, ConsoleModel> = {};
for (const brand of CONSOLE_BRANDS) {
  for (const m of brand.models) MODEL_INDEX[m.id] = m;
}

export function getModelById(id: string | null | undefined): ConsoleModel | undefined {
  if (!id) return undefined;
  return MODEL_INDEX[id];
}

export function brandIdForModel(modelId: string): ConsoleId | null {
  const model = getModelById(modelId);
  return model ? model.brandId : null;
}

// Pick a sensible default model for a given file extension.
// The engine only cares about the brand-level ID, so the specific model is a UX best-guess;
// the user can override in the selector.
const EXTENSION_DEFAULT_MODEL: Record<string, string> = {
  ".cle": "yamaha-cl5",
  ".clf": "yamaha-cl5",
  ".show": "digico-sd12",
};

export function detectModelFromFilename(filename: string): ConsoleModel | null {
  const dot = filename.lastIndexOf(".");
  if (dot === -1) return null;
  const ext = filename.slice(dot).toLowerCase();
  const id = EXTENSION_DEFAULT_MODEL[ext];
  return id ? (getModelById(id) ?? null) : null;
}

// ─── Legacy helpers kept for backward compatibility ─────────────────────────

const EXTENSION_MAP: Record<string, ConsoleId> = {
  ".cle": "yamaha_cl",
  ".clf": "yamaha_cl",
  ".show": "digico_sd",
};

export function detectConsole(filename: string): ConsoleId | null {
  const dot = filename.lastIndexOf(".");
  if (dot === -1) return null;
  const ext = filename.slice(dot).toLowerCase();
  return EXTENSION_MAP[ext] ?? null;
}

export function otherConsole(id: ConsoleId): ConsoleId {
  return id === "yamaha_cl" ? "digico_sd" : "yamaha_cl";
}

export function consoleLabel(id: string): string {
  return CONSOLES.find((c) => c.id === id)?.label ?? id;
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd web && npm run test -- tests/lib/consoles.test.ts
```

Expected: all tests pass.

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
cd web && npm run test
```

Expected: all existing tests still pass (ConsoleSelector, UploadFlow, etc. still use legacy exports).

- [ ] **Step 6: Commit**

```bash
git add web/src/lib/constants.ts web/tests/lib/consoles.test.ts
git commit -m "feat(web): expand console catalog with brand → model hierarchy"
```

---

## Task 3: Supabase migration — source_model, target_model, channel_names

**Files:**
- Create: `web/supabase/migrations/002_add_model_and_channel_names.sql`

- [ ] **Step 1: Create the migration file**

```sql
-- Add per-model identifiers alongside existing brand-level source_console/target_console.
alter table public.translations
  add column if not exists source_model text,
  add column if not exists target_model text,
  add column if not exists channel_names text[] not null default '{}';

-- Matching columns for anonymous previews so the anonymous → authenticated claim flow
-- can carry them forward without data loss.
alter table public.anonymous_previews
  add column if not exists source_model text,
  add column if not exists target_model text,
  add column if not exists channel_names text[] not null default '{}';
```

- [ ] **Step 2: Apply migration to the Supabase project**

This plan assumes migrations are applied via the Supabase CLI or dashboard. Do NOT execute this step without user confirmation — it mutates the live database.

User action:

```bash
# From repo root
cd web && npx supabase db push
```

Expected: new columns applied to both tables.

- [ ] **Step 3: Commit**

```bash
git add web/supabase/migrations/002_add_model_and_channel_names.sql
git commit -m "feat(db): add source_model, target_model, channel_names columns"
```

---

## Task 4: Timecode component

Renders relative time on top (bold, white) and absolute time below (muted), both right-aligned.

**Files:**
- Create: `web/src/components/Timecode.tsx`
- Create: `web/tests/components/Timecode.test.tsx`

- [ ] **Step 1: Write failing test**

Create `web/tests/components/Timecode.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Timecode from "@/components/Timecode";

describe("Timecode", () => {
  it("shows both relative and absolute lines for a recent timestamp", () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    render(<Timecode iso={twoHoursAgo} />);
    // Relative: some "hours ago" wording
    expect(screen.getByTestId("timecode-relative").textContent).toMatch(/hour/i);
    // Absolute: contains a day/month and a time
    const abs = screen.getByTestId("timecode-absolute").textContent ?? "";
    expect(abs).toMatch(/\d{1,2}:\d{2}/);
  });

  it("renders 'Yesterday' for a timestamp ~1 day old", () => {
    const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    render(<Timecode iso={yesterday} />);
    expect(screen.getByTestId("timecode-relative").textContent).toMatch(/day/i);
  });

  it("renders nothing useful for a missing timestamp but does not crash", () => {
    const { container } = render(<Timecode iso="" />);
    expect(container).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd web && npm run test -- tests/components/Timecode.test.tsx
```

Expected: fails with "Cannot find module '@/components/Timecode'".

- [ ] **Step 3: Implement the component**

Create `web/src/components/Timecode.tsx`:

```tsx
import { formatDistanceToNow } from "date-fns";

interface Props {
  iso: string;
}

export default function Timecode({ iso }: Props) {
  if (!iso) {
    return (
      <span className="flex flex-col items-end leading-tight">
        <span data-testid="timecode-relative" className="text-xs font-bold text-muted">—</span>
      </span>
    );
  }

  const date = new Date(iso);
  const relative = formatDistanceToNow(date, { addSuffix: true });

  const dateFmt = new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZoneName: "short",
  });
  const absolute = dateFmt.format(date);

  return (
    <span className="flex flex-col items-end leading-tight whitespace-nowrap">
      <span data-testid="timecode-relative" className="text-xs font-bold text-white">{relative}</span>
      <span data-testid="timecode-absolute" className="mt-0.5 text-[11px] text-muted">{absolute}</span>
    </span>
  );
}
```

- [ ] **Step 4: Run test — expect pass**

```bash
cd web && npm run test -- tests/components/Timecode.test.tsx
```

Expected: all three tests pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/Timecode.tsx web/tests/components/Timecode.test.tsx
git commit -m "feat(web): add Timecode component with relative + absolute local time"
```

---

## Task 5: DetailCard component

Renders a model summary card: heading, series subtitle, rows (max channels, mix buses, file format), and a footer status line. Used in the console selector and the report pane.

**Files:**
- Create: `web/src/components/DetailCard.tsx`
- Create: `web/tests/components/DetailCard.test.tsx`

- [ ] **Step 1: Write failing test**

Create `web/tests/components/DetailCard.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import DetailCard from "@/components/DetailCard";
import { getModelById } from "@/lib/constants";

describe("DetailCard", () => {
  it("renders source card with detected footer", () => {
    const cl5 = getModelById("yamaha-cl5")!;
    render(<DetailCard model={cl5} role="source" />);
    expect(screen.getByText("CL5")).toBeInTheDocument();
    expect(screen.getByText(/CL Series/i)).toBeInTheDocument();
    expect(screen.getByText("72")).toBeInTheDocument();
    expect(screen.getByText(/Detected from file/i)).toBeInTheDocument();
  });

  it("renders target card with supported footer", () => {
    const sd12 = getModelById("digico-sd12")!;
    render(<DetailCard model={sd12} role="target" />);
    expect(screen.getByText("SD12")).toBeInTheDocument();
    expect(screen.getByText(/Supported/i)).toBeInTheDocument();
  });

  it("renders warning state when warningMessage is provided", () => {
    const sd9 = getModelById("digico-sd9")!;
    render(<DetailCard model={sd9} role="target" warningMessage="24 channels will be dropped" />);
    expect(screen.getByText(/24 channels will be dropped/i)).toBeInTheDocument();
  });

  it("renders placeholder when no model selected", () => {
    render(<DetailCard model={undefined} role="target" />);
    expect(screen.getByText(/Select a target console/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd web && npm run test -- tests/components/DetailCard.test.tsx
```

Expected: fails (component doesn't exist).

- [ ] **Step 3: Implement the component**

Create `web/src/components/DetailCard.tsx`:

```tsx
import type { ConsoleModel } from "@/lib/constants";

interface Props {
  model: ConsoleModel | undefined;
  role: "source" | "target";
  warningMessage?: string;
}

export default function DetailCard({ model, role, warningMessage }: Props) {
  if (!model) {
    return (
      <div className="border border-border bg-surface px-4 py-6 text-center">
        <p className="text-xs text-muted">
          {role === "source" ? "Select a source console" : "Select a target console"}
        </p>
      </div>
    );
  }

  const isWarning = Boolean(warningMessage);
  const borderClass = isWarning ? "border-error/40" : "border-border";

  return (
    <div className={`border bg-surface px-4 py-4 ${borderClass}`}>
      <div className="flex items-start justify-between">
        <div>
          <h4 className="text-sm font-extrabold text-white">{model.model}</h4>
          <p className="mt-0.5 text-[10px] font-bold uppercase tracking-wider text-muted">
            {model.series} · {role === "source" ? "Source" : "Target"}
          </p>
        </div>
        {isWarning && (
          <span className="border border-error/40 px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-error">
            ⚠ Too small
          </span>
        )}
      </div>

      <div className="mt-3 flex flex-col gap-1.5">
        <Row label="Max channels" value={String(model.maxChannels)} warn={isWarning} />
        <Row label="Mix buses" value={String(model.mixBuses)} />
        <Row label="File format" value={model.fileFormat} />
      </div>

      <p
        className={`mt-3 border-t border-border pt-2 text-[10px] font-extrabold uppercase tracking-wider ${
          isWarning ? "text-error" : "text-success"
        }`}
      >
        {isWarning
          ? `⚠ ${warningMessage}`
          : role === "source"
          ? "✓ Detected from file"
          : "✓ Supported"}
      </p>
    </div>
  );
}

function Row({ label, value, warn = false }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[10px] font-bold uppercase tracking-wider text-muted">{label}</span>
      <span className={`text-xs font-bold ${warn ? "text-error" : "text-white"}`}>{value}</span>
    </div>
  );
}
```

- [ ] **Step 4: Run test — expect pass**

```bash
cd web && npm run test -- tests/components/DetailCard.test.tsx
```

Expected: all four tests pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/DetailCard.tsx web/tests/components/DetailCard.test.tsx
git commit -m "feat(web): add DetailCard component for console model summary"
```

---

## Task 6: CompatBar component

Full-width horizontal note shown under the console selector, green or red based on source/target channel counts.

**Files:**
- Create: `web/src/components/CompatBar.tsx`
- Create: `web/tests/components/CompatBar.test.tsx`

- [ ] **Step 1: Write failing test**

Create `web/tests/components/CompatBar.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import CompatBar from "@/components/CompatBar";

describe("CompatBar", () => {
  it("renders success message when target fits source", () => {
    render(<CompatBar sourceChannels={72} targetChannels={96} targetLabel="DiGiCo SD12" />);
    expect(screen.getByText(/fits/i)).toBeInTheDocument();
    expect(screen.getByText(/nothing will be dropped/i)).toBeInTheDocument();
  });

  it("renders warning when target is smaller than source", () => {
    render(<CompatBar sourceChannels={72} targetChannels={48} targetLabel="DiGiCo SD9" />);
    expect(screen.getByText(/49–72 will be dropped/)).toBeInTheDocument();
  });

  it("is a no-op when either value is missing", () => {
    const { container } = render(<CompatBar sourceChannels={undefined} targetChannels={96} targetLabel="X" />);
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd web && npm run test -- tests/components/CompatBar.test.tsx
```

Expected: fails (component doesn't exist).

- [ ] **Step 3: Implement the component**

Create `web/src/components/CompatBar.tsx`:

```tsx
interface Props {
  sourceChannels: number | undefined;
  targetChannels: number | undefined;
  targetLabel: string;
}

export default function CompatBar({ sourceChannels, targetChannels, targetLabel }: Props) {
  if (sourceChannels == null || targetChannels == null) return null;

  const fits = targetChannels >= sourceChannels;

  if (fits) {
    return (
      <div className="flex items-start gap-2 border border-success/30 bg-success/[0.06] px-4 py-3 text-xs text-success">
        <span>✓</span>
        <span>
          Source has <strong className="text-white">{sourceChannels} channels</strong> — {targetLabel}{" "}
          supports up to <strong className="text-white">{targetChannels}</strong>. Full translation, nothing will be
          dropped.
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2 border border-error/30 bg-error/[0.06] px-4 py-3 text-xs text-error">
      <span>⚠</span>
      <span>
        {targetLabel} supports only <strong className="text-white">{targetChannels} channels</strong> but your file
        has <strong className="text-white">{sourceChannels}</strong> — channels{" "}
        <strong className="text-white">
          {targetChannels + 1}–{sourceChannels}
        </strong>{" "}
        will be dropped.
      </span>
    </div>
  );
}
```

- [ ] **Step 4: Run test — expect pass**

```bash
cd web && npm run test -- tests/components/CompatBar.test.tsx
```

Expected: all three tests pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/CompatBar.tsx web/tests/components/CompatBar.test.tsx
git commit -m "feat(web): add CompatBar component for source/target channel comparison"
```

---

## Task 7: Rewrite ConsoleSelector

Replace the two-flat-dropdown selector with the brand-sidebar + model-search-and-chips design, integrating DetailCard and CompatBar.

**Files:**
- Modify: `web/src/components/ConsoleSelector.tsx` (full rewrite)
- Modify: `web/tests/components/ConsoleSelector.test.tsx` (rewrite — existing test asserts old API)

- [ ] **Step 1: Rewrite the test first**

Replace the full contents of `web/tests/components/ConsoleSelector.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ConsoleSelector from "@/components/ConsoleSelector";
import { getModelById } from "@/lib/constants";

describe("ConsoleSelector (new)", () => {
  it("renders two panels with labels", () => {
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd12"
        onSourceChange={vi.fn()}
        onTargetChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/Source Console/i)).toBeInTheDocument();
    expect(screen.getByText(/Target Console/i)).toBeInTheDocument();
  });

  it("shows the Auto-detected banner on the source side when sourceDetected is true", () => {
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd12"
        onSourceChange={vi.fn()}
        onTargetChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/Auto-detected/i)).toBeInTheDocument();
    expect(screen.getByText(/Override/i)).toBeInTheDocument();
  });

  it("clicking a brand in the target sidebar changes which models are listed", () => {
    const onTargetChange = vi.fn();
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd12"
        onSourceChange={vi.fn()}
        onTargetChange={onTargetChange}
      />,
    );
    // Target side starts on DiGiCo — SD12 chip visible.
    expect(screen.getByText("SD12")).toBeInTheDocument();
    // Click Yamaha on the target sidebar (pick the rightmost "Yamaha" button).
    const yamahaButtons = screen.getAllByText("Yamaha");
    fireEvent.click(yamahaButtons[yamahaButtons.length - 1]);
    // Now Yamaha CL/QL models appear on the target side.
    expect(screen.getAllByText("CL5").length).toBeGreaterThan(0);
    expect(screen.getAllByText("QL5").length).toBeGreaterThan(0);
  });

  it("clicking a target model chip invokes onTargetChange", () => {
    const onTargetChange = vi.fn();
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd12"
        onSourceChange={vi.fn()}
        onTargetChange={onTargetChange}
      />,
    );
    fireEvent.click(screen.getByText("Quantum 338"));
    expect(onTargetChange).toHaveBeenCalledWith("digico-quantum-338");
  });

  it("shows a warning compat bar when target is smaller than source", () => {
    // CL5 = 72 ch, SD9 = 48 ch
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd9"
        onSourceChange={vi.fn()}
        onTargetChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/49–72 will be dropped/)).toBeInTheDocument();
  });

  it("detail cards appear under each panel", () => {
    render(
      <ConsoleSelector
        sourceModelId="yamaha-cl5"
        sourceDetected
        targetModelId="digico-sd12"
        onSourceChange={vi.fn()}
        onTargetChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/Detected from file/i)).toBeInTheDocument();
    expect(screen.getByText(/Supported/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd web && npm run test -- tests/components/ConsoleSelector.test.tsx
```

Expected: tests fail because the selector still has the old API (expects `source`, `target`, `onSourceChange` with `ConsoleId` not model IDs).

- [ ] **Step 3: Rewrite the component**

Replace full contents of `web/src/components/ConsoleSelector.tsx`:

```tsx
"use client";

import { useState, useMemo } from "react";
import { CONSOLE_BRANDS, getModelById, type ConsoleModel } from "@/lib/constants";
import DetailCard from "./DetailCard";
import CompatBar from "./CompatBar";

interface Props {
  sourceModelId: string | undefined;
  sourceDetected: boolean;
  targetModelId: string | undefined;
  onSourceChange: (modelId: string) => void;
  onTargetChange: (modelId: string) => void;
  disabled?: boolean;
}

export default function ConsoleSelector({
  sourceModelId,
  sourceDetected,
  targetModelId,
  onSourceChange,
  onTargetChange,
  disabled = false,
}: Props) {
  const sourceModel = getModelById(sourceModelId);
  const targetModel = getModelById(targetModelId);

  // Which brand is active on each side. Initialise from the selected model if any.
  const [sourceBrand, setSourceBrand] = useState<string>(sourceModel?.brand ?? "Yamaha");
  const [targetBrand, setTargetBrand] = useState<string>(targetModel?.brand ?? "DiGiCo");

  // Override state — if true, the source side shows the brand-sidebar + search (just like target).
  const [overriding, setOverriding] = useState(false);
  const showSourceOverride = overriding || !sourceDetected;

  // Warning logic for the target detail card.
  const warningMessage = useMemo(() => {
    if (!sourceModel || !targetModel) return undefined;
    if (targetModel.maxChannels >= sourceModel.maxChannels) return undefined;
    const dropped = sourceModel.maxChannels - targetModel.maxChannels;
    return `${dropped} channels will be dropped`;
  }, [sourceModel, targetModel]);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-[1fr_36px_1fr] items-start gap-0">
        {/* Labels */}
        <p className="col-start-1 row-start-1 text-[10px] font-extrabold uppercase tracking-wider text-muted mb-2">
          Source Console
        </p>
        <p className="col-start-3 row-start-1 text-[10px] font-extrabold uppercase tracking-wider text-muted mb-2">
          Target Console
        </p>

        {/* Source panel */}
        <div className="col-start-1 row-start-2">
          <Panel
            activeBrand={sourceBrand}
            onBrandClick={setSourceBrand}
            selectedModelId={sourceModelId}
            onModelClick={onSourceChange}
            disabled={disabled}
            autoDetected={showSourceOverride ? false : sourceDetected}
            onOverrideClick={() => setOverriding(true)}
          />
        </div>

        {/* Arrow */}
        <div className="col-start-2 row-start-2 flex h-full items-center justify-center text-muted">→</div>

        {/* Target panel */}
        <div className="col-start-3 row-start-2">
          <Panel
            activeBrand={targetBrand}
            onBrandClick={setTargetBrand}
            selectedModelId={targetModelId}
            onModelClick={onTargetChange}
            disabled={disabled}
            autoDetected={false}
          />
        </div>

        {/* Detail cards */}
        <div className="col-start-1 row-start-3 mt-2">
          <DetailCard model={sourceModel} role="source" />
        </div>
        <div className="col-start-3 row-start-3 mt-2">
          <DetailCard model={targetModel} role="target" warningMessage={warningMessage} />
        </div>
      </div>

      {sourceModel && targetModel && (
        <CompatBar
          sourceChannels={sourceModel.maxChannels}
          targetChannels={targetModel.maxChannels}
          targetLabel={`${targetModel.brand} ${targetModel.model}`}
        />
      )}
    </div>
  );
}

// ── Panel (shared by both sides) ───────────────────────────────────────────

interface PanelProps {
  activeBrand: string;
  onBrandClick: (brand: string) => void;
  selectedModelId: string | undefined;
  onModelClick: (modelId: string) => void;
  disabled: boolean;
  autoDetected: boolean;
  onOverrideClick?: () => void;
}

function Panel({
  activeBrand,
  onBrandClick,
  selectedModelId,
  onModelClick,
  disabled,
  autoDetected,
  onOverrideClick,
}: PanelProps) {
  const [query, setQuery] = useState("");
  const brand = CONSOLE_BRANDS.find((b) => b.name === activeBrand) ?? CONSOLE_BRANDS[0];
  const filtered = brand.models.filter((m) =>
    m.model.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="flex border border-border bg-surface">
      {/* Brand sidebar */}
      <div className="w-[130px] shrink-0 border-r border-border bg-[#0d0d0d] p-2">
        <p className="px-1 pb-2 text-[9px] font-extrabold uppercase tracking-widest text-muted">Brand</p>
        {CONSOLE_BRANDS.map((b) => {
          const active = b.name === activeBrand;
          return (
            <button
              key={b.name}
              type="button"
              disabled={disabled}
              onClick={() => onBrandClick(b.name)}
              className={`block w-full text-left px-2 py-2 text-xs whitespace-nowrap disabled:opacity-50 ${
                active ? "bg-accent/10 text-accent font-bold" : "text-muted hover:text-white hover:bg-[#161616]"
              }`}
            >
              {b.name}
            </button>
          );
        })}
      </div>

      {/* Model panel */}
      <div className="flex-1 min-w-0 p-3 flex flex-col gap-2">
        {autoDetected ? (
          <div className="flex items-center gap-2 border border-success/30 bg-success/[0.06] px-3 py-2 text-[11px] text-success">
            <span>✓ Auto-detected</span>
            <button
              type="button"
              onClick={onOverrideClick}
              className="ml-auto text-accent font-bold hover:underline"
            >
              Override
            </button>
          </div>
        ) : (
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Filter ${activeBrand} models…`}
            disabled={disabled}
            className="w-full border border-border bg-bg px-3 py-2 text-xs text-white outline-none focus:border-accent disabled:opacity-50"
          />
        )}

        <div className="flex flex-wrap gap-1.5">
          {filtered.map((m) => {
            const selected = m.id === selectedModelId;
            return (
              <button
                key={m.id}
                type="button"
                disabled={disabled}
                onClick={() => onModelClick(m.id)}
                className={`inline-flex items-center gap-1 border px-3 py-1.5 text-xs font-semibold disabled:opacity-50 ${
                  selected
                    ? "bg-accent/10 border-accent text-accent"
                    : "border-border bg-surface text-white/80 hover:border-muted"
                }`}
              >
                <span>{m.model}</span>
                <span className="text-[10px] text-muted">{m.maxChannels} ch</span>
              </button>
            );
          })}
          {filtered.length === 0 && (
            <p className="text-[11px] text-muted">No models match “{query}”.</p>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test — expect pass**

```bash
cd web && npm run test -- tests/components/ConsoleSelector.test.tsx
```

Expected: all six tests pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/ConsoleSelector.tsx web/tests/components/ConsoleSelector.test.tsx
git commit -m "feat(web): rewrite ConsoleSelector with brand sidebar + model search"
```

---

## Task 8: Rewrite UploadFlow for file-first flow

Remove the pre-file console selector. Drop zone is the only thing visible pre-drop. After file drop, source is detected, target defaults to `digico-sd12` (or the other brand's first model if source is DiGiCo), and the full selector appears.

**Files:**
- Modify: `web/src/components/UploadFlow.tsx` (substantial rewrite)
- Modify: `web/tests/components/UploadFlow.test.tsx` (rewrite — current test asserts old flow)

- [ ] **Step 1: Rewrite the test**

Replace full contents of `web/tests/components/UploadFlow.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import UploadFlow from "@/components/UploadFlow";

function fileWithName(name: string) {
  return new File(["dummy"], name, { type: "application/octet-stream" });
}

describe("UploadFlow (file-first)", () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  it("shows only the dropzone in State A (no file)", () => {
    render(<UploadFlow />);
    expect(screen.getByText(/Drop your show file/i)).toBeInTheDocument();
    // Selector not visible yet
    expect(screen.queryByText(/Source Console/i)).not.toBeInTheDocument();
  });

  it("after selecting a .clf file, the selector appears with Yamaha CL5 auto-detected", () => {
    render(<UploadFlow />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(input, "files", {
      value: [fileWithName("show.clf")],
      configurable: true,
    });
    fireEvent.change(input);

    expect(screen.getByText(/Source Console/i)).toBeInTheDocument();
    expect(screen.getByText(/Auto-detected/i)).toBeInTheDocument();
    // CL5 chip is active
    expect(screen.getByText("CL5")).toBeInTheDocument();
    // Translate button appears
    expect(screen.getByRole("button", { name: /Translate/i })).toBeInTheDocument();
  });

  it("uploading calls /api/translate with both model and brand ids", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({
        translationId: "t1",
        channelCount: 72,
        translatedParams: [],
        approximatedParams: [],
        droppedParams: [],
        authenticated: true,
      }),
    } as unknown as Response);

    render(<UploadFlow />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(input, "files", {
      value: [fileWithName("show.clf")],
      configurable: true,
    });
    fireEvent.change(input);

    fireEvent.click(screen.getByRole("button", { name: /Translate/i }));

    // Give the fetch a tick
    await Promise.resolve();

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/translate",
      expect.objectContaining({ method: "POST" }),
    );
    const body = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body as FormData;
    expect(body.get("source_console")).toBe("yamaha_cl");
    expect(body.get("source_model")).toBe("yamaha-cl5");
    expect(body.get("target_model")).toBeTruthy();
  });

  it("clicking Start Over returns to State A", () => {
    render(<UploadFlow />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    Object.defineProperty(input, "files", {
      value: [fileWithName("show.clf")],
      configurable: true,
    });
    fireEvent.change(input);
    expect(screen.getByText(/Source Console/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Start Over/i }));
    expect(screen.queryByText(/Source Console/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Drop your show file/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd web && npm run test -- tests/components/UploadFlow.test.tsx
```

Expected: failures because the old flow shows `ConsoleSelector` in State A with no file.

- [ ] **Step 3: Rewrite the component**

Replace full contents of `web/src/components/UploadFlow.tsx`:

```tsx
"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import ConsoleSelector from "./ConsoleSelector";
import TranslationPreview from "./TranslationPreview";
import VerifyBanner from "./VerifyBanner";
import SignupWall from "./SignupWall";
import {
  detectModelFromFilename,
  getModelById,
  brandIdForModel,
  type ConsoleModel,
} from "@/lib/constants";

type FlowState = "idle" | "configuring" | "uploading" | "preview" | "error";

interface PreviewData {
  translationId: string;
  channelCount: number;
  translatedParams: string[];
  approximatedParams: string[];
  droppedParams: string[];
  authenticated: boolean;
}

const DEFAULT_TARGET_FOR_SOURCE_BRAND: Record<string, string> = {
  Yamaha: "digico-sd12",
  DiGiCo: "yamaha-cl5",
  "Allen & Heath": "digico-sd12",
  Midas: "digico-sd12",
  "SSL Live": "digico-sd12",
};

export default function UploadFlow() {
  const router = useRouter();
  const [state, setState] = useState<FlowState>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [sourceModelId, setSourceModelId] = useState<string | undefined>();
  const [sourceDetected, setSourceDetected] = useState(false);
  const [targetModelId, setTargetModelId] = useState<string | undefined>();
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSignupWall, setShowSignupWall] = useState(false);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    const detected = detectModelFromFilename(f.name);
    if (detected) {
      setSourceModelId(detected.id);
      setSourceDetected(true);
      setTargetModelId(DEFAULT_TARGET_FOR_SOURCE_BRAND[detected.brand] ?? "digico-sd12");
    } else {
      setSourceModelId(undefined);
      setSourceDetected(false);
      setTargetModelId(undefined);
    }
    setState("configuring");
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  const handleReset = () => {
    setState("idle");
    setFile(null);
    setSourceModelId(undefined);
    setSourceDetected(false);
    setTargetModelId(undefined);
    setPreview(null);
    setError(null);
  };

  const sourceModel: ConsoleModel | undefined = getModelById(sourceModelId);
  const targetModel: ConsoleModel | undefined = getModelById(targetModelId);
  const canTranslate = state === "configuring" && !!file && !!sourceModel && !!targetModel;

  const handleTranslate = async () => {
    if (!canTranslate) return;
    setState("uploading");
    setError(null);

    const formData = new FormData();
    formData.append("file", file!);
    formData.append("source_console", brandIdForModel(sourceModelId!)!);
    formData.append("target_console", brandIdForModel(targetModelId!)!);
    formData.append("source_model", sourceModelId!);
    formData.append("target_model", targetModelId!);

    try {
      const res = await fetch("/api/translate", { method: "POST", body: formData });
      const data = await res.json();

      if (!res.ok) {
        if (res.status === 402) {
          setError(
            "Coming soon — payments launching soon. You've already used your free translation.",
          );
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

  return (
    <div className="flex flex-col gap-6">
      {showSignupWall && (
        <SignupWall onClose={() => setShowSignupWall(false)} onSuccess={handleSignupSuccess} />
      )}

      {/* ── State A: idle ── */}
      {state === "idle" && (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="relative flex flex-col items-center justify-center border-2 border-dashed border-border bg-surface p-12 text-center transition-colors hover:border-accent/40 hover:bg-accent/[0.03]"
        >
          <p className="text-sm font-extrabold uppercase tracking-wider text-white">
            Drop your show file here
          </p>
          <p className="mt-1 text-xs text-muted">Source console will be detected automatically</p>
          <p className="mt-3 text-[10px] text-muted">.clf · .cle · .show</p>
          <div className="mt-4 inline-block bg-accent px-5 py-2 text-xs font-extrabold uppercase tracking-wider text-black">
            Choose File
          </div>
          <input
            type="file"
            accept=".cle,.clf,.show"
            onChange={handleFileInput}
            className="absolute inset-0 cursor-pointer opacity-0"
          />
        </div>
      )}

      {/* ── State B: configuring ── */}
      {state === "configuring" && file && (
        <>
          <div className="flex items-center gap-3 border border-success/30 bg-success/[0.06] px-4 py-3">
            <span className="text-xl">📄</span>
            <div>
              <p className="text-sm font-bold text-white">{file.name}</p>
              {sourceDetected && sourceModel && (
                <p className="mt-0.5 text-xs text-success">
                  ✓ Detected: {sourceModel.brand} {sourceModel.model} — {sourceModel.maxChannels}{" "}
                  input channels, {sourceModel.mixBuses} mix buses
                </p>
              )}
              {!sourceDetected && (
                <p className="mt-0.5 text-xs text-warning">
                  ⚠ Could not auto-detect — pick the source console below
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={handleReset}
              className="ml-auto text-xs font-extrabold uppercase tracking-wider text-muted hover:text-white"
            >
              Start Over
            </button>
          </div>

          <ConsoleSelector
            sourceModelId={sourceModelId}
            sourceDetected={sourceDetected}
            targetModelId={targetModelId}
            onSourceChange={(id) => {
              setSourceModelId(id);
              setSourceDetected(false);
            }}
            onTargetChange={setTargetModelId}
          />

          <button
            type="button"
            onClick={handleTranslate}
            disabled={!canTranslate}
            className="w-full bg-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300 disabled:opacity-40"
          >
            Translate →
          </button>
        </>
      )}

      {/* ── State: uploading ── */}
      {state === "uploading" && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <p className="text-sm font-extrabold uppercase tracking-wider text-accent">Translating...</p>
          <p className="mt-2 text-xs text-muted">
            Parsing your show file and mapping to the target console.
          </p>
        </div>
      )}

      {/* ── State: preview ── */}
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
          {preview.authenticated ? (
            <div className="flex flex-col gap-3">
              <a
                href={`/api/download/${preview.translationId}?type=output`}
                className="flex items-center justify-center bg-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-black no-underline hover:bg-yellow-300"
              >
                Download translated file
              </a>
              <a
                href={`/api/download/${preview.translationId}?type=report`}
                className="flex items-center justify-center border border-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-accent no-underline hover:bg-accent/10"
              >
                Download translation report (PDF)
              </a>
              <button
                type="button"
                onClick={() => router.push(`/translations/${preview.translationId}`)}
                className="text-xs text-muted hover:text-white"
              >
                View full details
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleDownload}
              className="bg-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300"
            >
              Download translated file
            </button>
          )}
          <button type="button" onClick={handleReset} className="text-xs text-muted hover:text-white">
            Translate another file
          </button>
        </div>
      )}

      {/* ── State: error ── */}
      {state === "error" && (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <p className="text-sm font-bold text-error">{error}</p>
          <button
            type="button"
            onClick={handleReset}
            className="text-xs text-accent hover:underline"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd web && npm run test -- tests/components/UploadFlow.test.tsx
```

Expected: all four new tests pass.

- [ ] **Step 5: Run full test suite**

```bash
cd web && npm run test
```

Expected: all tests across the repo still pass.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/UploadFlow.tsx web/tests/components/UploadFlow.test.tsx
git commit -m "feat(web): rewrite UploadFlow for file-first flow with inline selector"
```

---

## Task 9: Update /api/translate to store source_model, target_model, channel_names

The POST route needs to read the two new fields from the form data and persist them. `channel_names` is passed through from the engine response where present (currently always empty — graceful fallback).

**Files:**
- Modify: `web/src/app/api/translate/route.ts`

- [ ] **Step 1: Inspect the current route and add the columns to the insert**

Read the current route:

```bash
cd web && cat src/app/api/translate/route.ts
```

Locate the `supabase.from("translations").insert(...)` call. Add these two reads before the insert:

```ts
const sourceModel = formData.get("source_model") as string | null;
const targetModel = formData.get("target_model") as string | null;
```

Add these fields into the insert payload:

```ts
source_model: sourceModel,
target_model: targetModel,
channel_names: [],
```

Do the same for the anonymous-preview code path if it exists in this route (check `supabase.from("anonymous_previews").insert(...)`). Mirror the same three new fields.

- [ ] **Step 2: Verify the build succeeds**

```bash
cd web && npm run build
```

Expected: build passes with no type errors related to the translate route.

- [ ] **Step 3: Run tests**

```bash
cd web && npm run test
```

Expected: all tests still pass.

- [ ] **Step 4: Commit**

```bash
git add web/src/app/api/translate/route.ts
git commit -m "feat(api): persist source_model, target_model, channel_names on translate"
```

---

## Task 10: ReportPane component

The right-side detail pane that opens when you click a translation in the history list.

**Files:**
- Create: `web/src/components/ReportPane.tsx`
- Create: `web/tests/components/ReportPane.test.tsx`

- [ ] **Step 1: Write failing test**

Create `web/tests/components/ReportPane.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ReportPane from "@/components/ReportPane";

const baseTranslation = {
  id: "t1",
  source_console: "yamaha_cl",
  target_console: "digico_sd",
  source_model: "yamaha-cl5",
  target_model: "digico-sd12",
  source_filename: "festival.clf",
  channel_count: 72,
  translated_params: ["channel_names", "hpf", "eq_4_band"],
  approximated_params: ["eq_q_bands_3_4"],
  dropped_params: ["premium_rack"],
  channel_names: ["KICK", "SNARE TOP", "BASS DI"],
  status: "complete",
  created_at: new Date().toISOString(),
};

describe("ReportPane", () => {
  it("renders filename and route subtitle", () => {
    render(<ReportPane translation={baseTranslation} onClose={vi.fn()} />);
    expect(screen.getByText("festival.clf")).toBeInTheDocument();
    expect(screen.getByText(/72 ch/i)).toBeInTheDocument();
  });

  it("shows summary chips with counts", () => {
    render(<ReportPane translation={baseTranslation} onClose={vi.fn()} />);
    expect(screen.getByText(/✓ 3/)).toBeInTheDocument();
    expect(screen.getByText(/~ 1/)).toBeInTheDocument();
    expect(screen.getByText(/× 1/)).toBeInTheDocument();
  });

  it("lists translated / approximated / dropped params", () => {
    render(<ReportPane translation={baseTranslation} onClose={vi.fn()} />);
    expect(screen.getByText(/Channel Names/i)).toBeInTheDocument(); // section label
    expect(screen.getByText(/Hpf/i)).toBeInTheDocument();
    expect(screen.getByText(/Premium Rack/i)).toBeInTheDocument();
  });

  it("renders channel name cells", () => {
    render(<ReportPane translation={baseTranslation} onClose={vi.fn()} />);
    expect(screen.getByText("KICK")).toBeInTheDocument();
    expect(screen.getByText("SNARE TOP")).toBeInTheDocument();
  });

  it("shows a graceful fallback when channel_names is empty", () => {
    render(
      <ReportPane
        translation={{ ...baseTranslation, channel_names: [] }}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/Channel names not stored/i)).toBeInTheDocument();
  });

  it("calls onClose when the ✕ is clicked", () => {
    const onClose = vi.fn();
    render(<ReportPane translation={baseTranslation} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd web && npm run test -- tests/components/ReportPane.test.tsx
```

Expected: fails (component doesn't exist).

- [ ] **Step 3: Implement the component**

Create `web/src/components/ReportPane.tsx`:

```tsx
import { consoleLabel } from "@/lib/constants";

interface Translation {
  id: string;
  source_console: string;
  target_console: string;
  source_model?: string | null;
  target_model?: string | null;
  source_filename: string;
  channel_count: number;
  translated_params: string[];
  approximated_params: string[];
  dropped_params: string[];
  channel_names: string[];
  status: string;
  created_at: string;
}

interface Props {
  translation: Translation;
  onClose: () => void;
}

function formatParam(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ReportPane({ translation: t, onClose }: Props) {
  const route = `${consoleLabel(t.source_console)} → ${consoleLabel(t.target_console)}`;
  const tx = t.translated_params.length;
  const ap = t.approximated_params.length;
  const dr = t.dropped_params.length;

  return (
    <aside className="w-[300px] shrink-0 border-l border-border bg-[#0d0d0d] p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-extrabold text-white break-words">{t.source_filename}</h4>
          <p className="mt-1 text-[10px] font-bold uppercase tracking-wider text-muted">
            {route} · {t.channel_count} ch
          </p>
        </div>
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="text-muted hover:text-white"
        >
          ✕
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {tx > 0 && (
          <span className="border border-success/30 bg-success/[0.06] px-2 py-0.5 text-[10px] font-bold text-success">
            ✓ {tx}
          </span>
        )}
        {ap > 0 && (
          <span className="border border-warning/30 bg-warning/[0.06] px-2 py-0.5 text-[10px] font-bold text-warning">
            ~ {ap}
          </span>
        )}
        {dr > 0 && (
          <span className="border border-error/30 bg-error/[0.06] px-2 py-0.5 text-[10px] font-bold text-error">
            × {dr}
          </span>
        )}
      </div>

      <Section title="✓ Translated" color="text-success">
        {t.translated_params.map((p) => (
          <ParamItem key={p}>{formatParam(p)}</ParamItem>
        ))}
      </Section>

      {ap > 0 && (
        <Section title="~ Approximated" color="text-warning">
          {t.approximated_params.map((p) => (
            <ParamItem key={p}>{formatParam(p)}</ParamItem>
          ))}
        </Section>
      )}

      {dr > 0 && (
        <Section title="× Dropped" color="text-error">
          {t.dropped_params.map((p) => (
            <ParamItem key={p}>{formatParam(p)}</ParamItem>
          ))}
        </Section>
      )}

      <Section title="Channel Names" color="text-muted">
        {t.channel_names.length === 0 ? (
          <p className="text-[11px] text-muted italic">Channel names not stored for this translation.</p>
        ) : (
          <div className="grid grid-cols-2 gap-1">
            {t.channel_names.slice(0, 24).map((n, i) => (
              <div
                key={`${n}-${i}`}
                className="border border-border bg-surface px-2 py-1 text-[11px] text-white/80 overflow-hidden text-ellipsis whitespace-nowrap"
              >
                {n}
              </div>
            ))}
            {t.channel_names.length > 24 && (
              <p className="col-span-2 text-[10px] text-muted">+{t.channel_names.length - 24} more…</p>
            )}
          </div>
        )}
      </Section>

      <a
        href={`/api/download/${t.id}?type=output`}
        className="mt-4 block w-full bg-accent px-4 py-2.5 text-center text-xs font-extrabold uppercase tracking-wider text-black no-underline hover:bg-yellow-300"
      >
        Download .show
      </a>
    </aside>
  );
}

function Section({
  title,
  color,
  children,
}: {
  title: string;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-4">
      <p className={`text-[10px] font-extrabold uppercase tracking-wider ${color}`}>{title}</p>
      <div className="mt-1 flex flex-col gap-0.5">{children}</div>
    </div>
  );
}

function ParamItem({ children }: { children: React.ReactNode }) {
  return (
    <p className="border-b border-border/50 py-1 text-[11px] text-white/70 last:border-b-0">
      {children}
    </p>
  );
}
```

- [ ] **Step 4: Run test — expect pass**

```bash
cd web && npm run test -- tests/components/ReportPane.test.tsx
```

Expected: all six tests pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/ReportPane.tsx web/tests/components/ReportPane.test.tsx
git commit -m "feat(web): add ReportPane for inline translation detail view"
```

---

## Task 11: Rewrite TranslationHistory with two-pane layout + summary chips

**Files:**
- Modify: `web/src/components/TranslationHistory.tsx` (full rewrite, convert to Client Component since it owns selected-row state)
- Create: `web/tests/components/TranslationHistory.test.tsx` (new — no existing test)

- [ ] **Step 1: Write failing test**

Create `web/tests/components/TranslationHistory.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import TranslationHistory from "@/components/TranslationHistory";

const rows = [
  {
    id: "a",
    source_console: "yamaha_cl",
    target_console: "digico_sd",
    source_model: "yamaha-cl5",
    target_model: "digico-sd12",
    source_filename: "festival.clf",
    channel_count: 72,
    translated_params: ["hpf", "eq"],
    approximated_params: [],
    dropped_params: ["premium_rack"],
    channel_names: ["KICK", "SNARE"],
    status: "complete",
    created_at: new Date().toISOString(),
  },
  {
    id: "b",
    source_console: "yamaha_cl",
    target_console: "digico_sd",
    source_model: "yamaha-ql5",
    target_model: "digico-sd12",
    source_filename: "monitor.clf",
    channel_count: 48,
    translated_params: ["hpf"],
    approximated_params: [],
    dropped_params: [],
    channel_names: [],
    status: "complete",
    created_at: new Date(Date.now() - 24 * 3600 * 1000).toISOString(),
  },
];

describe("TranslationHistory", () => {
  it("renders a row per translation with summary chips", () => {
    render(<TranslationHistory translations={rows} />);
    expect(screen.getByText("festival.clf")).toBeInTheDocument();
    expect(screen.getByText("monitor.clf")).toBeInTheDocument();
    expect(screen.getByText(/✓ 2/)).toBeInTheDocument();
    expect(screen.getByText(/× 1/)).toBeInTheDocument();
  });

  it("renders empty state when no translations", () => {
    render(<TranslationHistory translations={[]} />);
    expect(screen.getByText(/No translations yet/i)).toBeInTheDocument();
  });

  it("clicking a row opens the ReportPane", () => {
    render(<TranslationHistory translations={rows} />);
    // ReportPane not present initially
    expect(screen.queryByRole("button", { name: /close/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("festival.clf"));
    expect(screen.getByRole("button", { name: /close/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd web && npm run test -- tests/components/TranslationHistory.test.tsx
```

Expected: fails — current `TranslationHistory` renders links, not click-openable rows, and has no ReportPane.

- [ ] **Step 3: Rewrite the component**

Replace full contents of `web/src/components/TranslationHistory.tsx`:

```tsx
"use client";

import { useState } from "react";
import { consoleLabel } from "@/lib/constants";
import Timecode from "./Timecode";
import ReportPane from "./ReportPane";

export interface Translation {
  id: string;
  source_console: string;
  target_console: string;
  source_model?: string | null;
  target_model?: string | null;
  source_filename: string;
  channel_count: number;
  translated_params: string[];
  approximated_params: string[];
  dropped_params: string[];
  channel_names: string[];
  status: string;
  created_at: string;
}

interface Props {
  translations: Translation[];
}

export default function TranslationHistory({ translations }: Props) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const active = translations.find((t) => t.id === activeId) ?? null;

  if (translations.length === 0) {
    return (
      <div className="border border-border bg-surface px-6 py-10 text-center">
        <p className="text-sm text-muted">No translations yet.</p>
        <p className="mt-1 text-xs text-muted">Upload a show file above to get started.</p>
      </div>
    );
  }

  return (
    <div className="flex border border-border bg-surface">
      <div className="flex-1 min-w-0">
        {translations.map((t) => (
          <Row
            key={t.id}
            t={t}
            active={t.id === activeId}
            onClick={() => setActiveId(t.id === activeId ? null : t.id)}
          />
        ))}
      </div>
      {active && (
        <ReportPane translation={active} onClose={() => setActiveId(null)} />
      )}
    </div>
  );
}

function Row({
  t,
  active,
  onClick,
}: {
  t: Translation;
  active: boolean;
  onClick: () => void;
}) {
  const tx = t.translated_params.length;
  const ap = t.approximated_params.length;
  const dr = t.dropped_params.length;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-4 border-b border-border px-4 py-3 text-left last:border-b-0 hover:bg-[#131313] ${
        active ? "bg-[#131313] border-l-2 border-l-accent pl-[14px]" : ""
      }`}
    >
      <span className="text-lg shrink-0">📄</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-bold text-white truncate">{t.source_filename}</p>
        <p className="mt-0.5 text-[11px] text-muted truncate">
          {consoleLabel(t.source_console)} → {consoleLabel(t.target_console)}
        </p>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {tx > 0 && (
            <span className="border border-success/30 bg-success/[0.06] px-2 py-0.5 text-[10px] font-bold text-success">
              ✓ {tx} translated
            </span>
          )}
          {ap > 0 && (
            <span className="border border-warning/30 bg-warning/[0.06] px-2 py-0.5 text-[10px] font-bold text-warning">
              ~ {ap} approx
            </span>
          )}
          {dr > 0 && (
            <span className="border border-error/30 bg-error/[0.06] px-2 py-0.5 text-[10px] font-bold text-error">
              × {dr} dropped
            </span>
          )}
        </div>
      </div>
      <span className="text-[11px] text-muted whitespace-nowrap shrink-0">
        {t.channel_count} ch
      </span>
      <Timecode iso={t.created_at} />
      <span className="text-[10px] font-extrabold uppercase tracking-wider text-success shrink-0">
        {t.status === "complete" ? "Done" : t.status}
      </span>
    </button>
  );
}
```

- [ ] **Step 4: Run test — expect pass**

```bash
cd web && npm run test -- tests/components/TranslationHistory.test.tsx
```

Expected: all three tests pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/TranslationHistory.tsx web/tests/components/TranslationHistory.test.tsx
git commit -m "feat(web): TranslationHistory two-pane layout with summary chips"
```

---

## Task 12: Update Dashboard page layout

**Files:**
- Modify: `web/src/app/dashboard/page.tsx`

- [ ] **Step 1: Inspect fields selected from Supabase**

We need the query to include the new columns. Update the select string if it's narrower than `"*"` (it's currently `"*"`, which already covers them). Verify:

```bash
cd web && grep -n "from(\"translations\")" src/app/dashboard/page.tsx
```

- [ ] **Step 2: Replace page contents**

Replace full contents of `web/src/app/dashboard/page.tsx`:

```tsx
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import UploadFlow from "@/components/UploadFlow";
import TranslationHistory, { type Translation } from "@/components/TranslationHistory";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data } = await supabase
    .from("translations")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(20);

  const translations: Translation[] = (data ?? []).map((row) => ({
    id: row.id,
    source_console: row.source_console,
    target_console: row.target_console,
    source_model: row.source_model,
    target_model: row.target_model,
    source_filename: row.source_filename,
    channel_count: row.channel_count,
    translated_params: row.translated_params ?? [],
    approximated_params: row.approximated_params ?? [],
    dropped_params: row.dropped_params ?? [],
    channel_names: row.channel_names ?? [],
    status: row.status,
    created_at: row.created_at,
  }));

  return (
    <main className="py-12">
      <div className="mx-auto max-w-5xl px-6">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">★ Showfier</p>
        <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">Dashboard</h1>

        <div className="mt-8">
          <h2 className="text-[10px] font-extrabold uppercase tracking-wider text-muted">
            New Translation
          </h2>
          <div className="mt-3"><UploadFlow /></div>
        </div>

        <div className="mt-12">
          <h2 className="text-[10px] font-extrabold uppercase tracking-wider text-muted">
            Recent Translations
          </h2>
          <div className="mt-3">
            <TranslationHistory translations={translations} />
          </div>
        </div>
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd web && npm run build
```

Expected: build passes.

- [ ] **Step 4: Commit**

```bash
git add web/src/app/dashboard/page.tsx
git commit -m "feat(web): widen dashboard, merge upload + history layout"
```

---

## Task 13: Redirect /translate to / (anon) or /dashboard (authed)

**Files:**
- Modify: `web/src/app/translate/page.tsx`

- [ ] **Step 1: Replace the page with a redirect**

Replace full contents of `web/src/app/translate/page.tsx`:

```tsx
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export default async function TranslatePage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  redirect(user ? "/dashboard" : "/");
}
```

- [ ] **Step 2: Verify build**

```bash
cd web && npm run build
```

Expected: build passes.

- [ ] **Step 3: Commit**

```bash
git add web/src/app/translate/page.tsx
git commit -m "refactor(web): /translate now redirects to /dashboard or /"
```

---

## Task 14: Update `/translations/[id]` detail page to use Timecode

The detail page still uses `.toLocaleDateString()`. Swap it for the new Timecode component for consistency.

**Files:**
- Modify: `web/src/app/translations/[id]/page.tsx`

- [ ] **Step 1: Replace the date subtitle with Timecode**

In `web/src/app/translations/[id]/page.tsx`, locate the subtitle `<p>` with `new Date(translation.created_at).toLocaleDateString()`. Replace the whole paragraph with:

```tsx
<div className="mt-1 flex items-center gap-3 text-sm text-muted">
  <span>
    {consoleLabel(translation.source_console)} → {consoleLabel(translation.target_console)}
  </span>
  <Timecode iso={translation.created_at} />
</div>
```

Add the import at the top of the file:

```tsx
import Timecode from "@/components/Timecode";
```

- [ ] **Step 2: Verify build**

```bash
cd web && npm run build
```

Expected: build passes.

- [ ] **Step 3: Commit**

```bash
git add web/src/app/translations/[id]/page.tsx
git commit -m "refactor(web): detail page uses Timecode for timestamp"
```

---

## Task 15: Final verification — full test suite + dev smoke test

**Files:** none (verification only)

- [ ] **Step 1: Run full test suite**

```bash
cd web && npm run test
```

Expected: all tests pass. No regressions.

- [ ] **Step 2: Run production build**

```bash
cd web && npm run build
```

Expected: no type errors, no missing dependencies, successful build.

- [ ] **Step 3: Start dev server and smoke-test**

```bash
cd web && npm run dev
```

Open the browser to `http://localhost:3000/dashboard` (log in first if needed). Verify:

- Pre-drop: only the dropzone is visible.
- Drop a `.clf` file: source auto-detects to Yamaha CL5, target defaults to DiGiCo SD12, detail cards populated, compat bar green.
- Click a different target brand → models update.
- Click a target chip with fewer channels than source (e.g. DiGiCo SD9) → detail card goes red, compat bar goes red with "channels N–M will be dropped".
- Hit Start Over → back to dropzone.
- In the history list, click a row → ReportPane opens on the right with summary chips, param sections, and channel names (or fallback text).
- Click ✕ → pane closes.
- Timecodes show relative on top, absolute below, using the browser timezone.

- [ ] **Step 4: Tag a merge point**

If everything looks good, the branch is ready to merge/PR.

```bash
git status
```

Expected: clean working tree. All tasks committed individually.

---

## Appendix A: Out of scope

- Engine-side changes to return channel names (follow-up work).
- Per-model translation logic (engine still uses brand-level IDs).
- Mobile refinements beyond the stacked fallback mentioned in the spec.
- Search across brands inside a single selector panel.
- Saving a preferred default target console per user.

## Appendix B: Rollback notes

If something goes wrong after deploy:

- Migration `002_add_model_and_channel_names.sql` is additive — it will not break the legacy code path. Columns default to empty/null.
- UploadFlow still posts the legacy `source_console` / `target_console` form fields, so the translate API and engine work unchanged if the frontend reverts.
- To revert UI changes, revert the feature commits on this branch; DB migration can stay in place.
