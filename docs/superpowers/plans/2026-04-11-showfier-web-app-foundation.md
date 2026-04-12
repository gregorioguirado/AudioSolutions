# Showfier Web App Foundation — Plan 2a: Landing Page + Auth

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy a Next.js landing page with Supabase auth (signup, login, email verification) — the public-facing front door for Showfier.

**Architecture:** Next.js 14 App Router on Vercel. Tailwind CSS with a custom dark monospace theme (JetBrains Mono). Supabase handles auth (GoTrue) and Postgres. No translation flow yet — that's Plan 2b. The hero drop zone navigates to `/translate` (a placeholder page until Plan 2b).

**Tech Stack:** Next.js 14, React 18, TypeScript, Tailwind CSS, @supabase/ssr, Vitest, React Testing Library

**Spec:** `docs/superpowers/specs/2026-04-11-showfier-web-app-design.md`

---

## File Map

```
web/
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.mjs
├── vitest.config.ts
├── vitest.setup.ts
├── .env.local.example
├── public/
│   └── (empty — text wordmark, no logo files)
├── src/
│   ├── middleware.ts                 # Next.js auth middleware
│   ├── app/
│   │   ├── layout.tsx               # Root layout: font, nav, theme
│   │   ├── page.tsx                 # Landing page (/)
│   │   ├── globals.css              # Tailwind directives + custom CSS
│   │   ├── signup/
│   │   │   └── page.tsx             # Signup page
│   │   ├── login/
│   │   │   └── page.tsx             # Login page
│   │   ├── auth/
│   │   │   └── callback/
│   │   │       └── route.ts         # Email verification callback
│   │   ├── dashboard/
│   │   │   └── page.tsx             # Placeholder (Plan 2b)
│   │   └── translate/
│   │       └── page.tsx             # Placeholder (Plan 2b)
│   ├── components/
│   │   ├── Nav.tsx                  # Sticky navigation bar
│   │   ├── HeroDropZone.tsx         # Hero section (Option 1)
│   │   ├── HowItWorks.tsx           # Three-step flow section
│   │   ├── WhatTranslates.tsx       # Two-column translates/doesn't
│   │   ├── PricingTeaser.tsx        # Three-column pricing cards
│   │   ├── FAQ.tsx                  # Accordion FAQ
│   │   ├── Footer.tsx               # Footer
│   │   ├── SignupForm.tsx           # Signup form component
│   │   └── LoginForm.tsx            # Login form component
│   └── lib/
│       ├── constants.ts             # Console list, auto-detect
│       └── supabase/
│           ├── client.ts            # Browser Supabase client
│           ├── server.ts            # Server Supabase client
│           └── middleware.ts        # Supabase middleware helper
├── tests/
│   ├── lib/
│   │   └── constants.test.ts
│   └── components/
│       ├── Nav.test.tsx
│       ├── HeroDropZone.test.tsx
│       ├── LandingPage.test.tsx
│       ├── SignupForm.test.tsx
│       └── LoginForm.test.tsx
└── supabase/
    └── migrations/
        └── 001_initial_schema.sql
```

---

## Task 1: Project scaffold + Tailwind theme

**Files:**
- Create: `web/` directory via `create-next-app`
- Modify: `web/tailwind.config.ts`
- Create: `web/src/app/globals.css`
- Create: `web/.env.local.example`

- [ ] **Step 1: Create Next.js project**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
npx create-next-app@14 web --typescript --tailwind --eslint --app --src-dir --no-import-alias
```

When prompted for options, accept defaults. This creates the `web/` directory with Next.js 14, TypeScript, Tailwind, App Router, and `src/` directory.

- [ ] **Step 2: Install Supabase + testing dependencies**

```bash
cd web
npm install @supabase/supabase-js @supabase/ssr
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

- [ ] **Step 3: Configure Tailwind theme**

Replace `web/tailwind.config.ts`:

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0a",
        surface: "#111111",
        border: "#2a2a2a",
        accent: "#ffde00",
        success: "#34c759",
        warning: "#ffcc00",
        error: "#ff6b6b",
        muted: "#888888",
      },
      fontFamily: {
        mono: [
          "var(--font-jetbrains)",
          "JetBrains Mono",
          "SF Mono",
          "Menlo",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 4: Write global CSS**

Replace `web/src/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-bg text-white font-mono antialiased;
  }

  ::selection {
    @apply bg-accent text-black;
  }

  a {
    @apply text-accent hover:underline;
  }
}
```

- [ ] **Step 5: Set up root layout with JetBrains Mono font**

Replace `web/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
});

export const metadata: Metadata = {
  title: "Showfier — Stop Rebuilding Your Shows",
  description:
    "Upload a Yamaha CL/QL show file, download a DiGiCo SD/Quantum translation. 30 seconds.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={jetbrains.variable}>
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 6: Create .env.local.example**

Create `web/.env.local.example`:

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Translation engine
ENGINE_URL=https://audiosolutions-production.up.railway.app

# App
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

- [ ] **Step 7: Replace the default page with a minimal placeholder**

Replace `web/src/app/page.tsx`:

```tsx
export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <h1 className="text-4xl font-bold uppercase tracking-tight">
        ★ Showfier
      </h1>
    </main>
  );
}
```

- [ ] **Step 8: Verify the dev server runs**

```bash
cd web && npm run dev
```

Open `http://localhost:3000` in a browser. Expected: dark background (#0a0a0a), white "★ Showfier" in JetBrains Mono, centered on screen.

Press Ctrl+C to stop.

- [ ] **Step 9: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/ .gitignore
git commit -m "feat: scaffold Next.js app with Tailwind dark monospace theme"
```

---

## Task 2: Vitest setup + constants

**Files:**
- Create: `web/vitest.config.ts`
- Create: `web/vitest.setup.ts`
- Create: `web/src/lib/constants.ts`
- Create: `web/tests/lib/constants.test.ts`

- [ ] **Step 1: Write the failing test for auto-detect**

Create `web/tests/lib/constants.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { detectConsole, CONSOLES, otherConsole } from "../../src/lib/constants";

describe("detectConsole", () => {
  it("detects .cle as yamaha_cl", () => {
    expect(detectConsole("my_show.cle")).toBe("yamaha_cl");
  });

  it("detects .CLE as yamaha_cl (case-insensitive)", () => {
    expect(detectConsole("my_show.CLE")).toBe("yamaha_cl");
  });

  it("detects .show as digico_sd", () => {
    expect(detectConsole("festival.show")).toBe("digico_sd");
  });

  it("returns null for unknown extensions", () => {
    expect(detectConsole("notes.txt")).toBeNull();
  });

  it("returns null for no extension", () => {
    expect(detectConsole("README")).toBeNull();
  });
});

describe("otherConsole", () => {
  it("returns digico_sd for yamaha_cl", () => {
    expect(otherConsole("yamaha_cl")).toBe("digico_sd");
  });

  it("returns yamaha_cl for digico_sd", () => {
    expect(otherConsole("digico_sd")).toBe("yamaha_cl");
  });
});

describe("CONSOLES", () => {
  it("has exactly two entries", () => {
    expect(CONSOLES).toHaveLength(2);
  });

  it("each entry has id and label", () => {
    for (const c of CONSOLES) {
      expect(c).toHaveProperty("id");
      expect(c).toHaveProperty("label");
    }
  });
});
```

- [ ] **Step 2: Create Vitest config**

Create `web/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
  },
});
```

Create `web/vitest.setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd web && npx vitest run tests/lib/constants.test.ts
```

Expected: FAIL — `Cannot find module '../../src/lib/constants'`

- [ ] **Step 4: Write the constants module**

Create `web/src/lib/constants.ts`:

```ts
export const CONSOLES = [
  { id: "yamaha_cl", label: "Yamaha CL/QL" },
  { id: "digico_sd", label: "DiGiCo SD/Quantum" },
] as const;

export type ConsoleId = (typeof CONSOLES)[number]["id"];

const EXTENSION_MAP: Record<string, ConsoleId> = {
  ".cle": "yamaha_cl",
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

- [ ] **Step 5: Run test to verify it passes**

```bash
cd web && npx vitest run tests/lib/constants.test.ts
```

Expected: `6 passed`

- [ ] **Step 6: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/vitest.config.ts web/vitest.setup.ts web/src/lib/constants.ts web/tests/lib/constants.test.ts
git commit -m "feat: add vitest setup and console auto-detect logic"
```

---

## Task 3: Nav component

**Files:**
- Create: `web/src/components/Nav.tsx`
- Create: `web/tests/components/Nav.test.tsx`
- Modify: `web/src/app/layout.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/tests/components/Nav.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Nav from "../../src/components/Nav";

describe("Nav", () => {
  it("renders the Showfier brand mark", () => {
    render(<Nav />);
    expect(screen.getByText(/showfier/i)).toBeInTheDocument();
  });

  it("renders Login and Sign up links", () => {
    render(<Nav />);
    expect(screen.getByRole("link", { name: /log in/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign up/i })).toBeInTheDocument();
  });

  it("renders anchor links for How it works, Pricing, FAQ", () => {
    render(<Nav />);
    expect(
      screen.getByRole("link", { name: /how it works/i })
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /pricing/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /faq/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && npx vitest run tests/components/Nav.test.tsx
```

Expected: FAIL — `Cannot find module '../../src/components/Nav'`

- [ ] **Step 3: Implement the Nav component**

Create `web/src/components/Nav.tsx`:

```tsx
import Link from "next/link";

export default function Nav() {
  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between border-b border-border bg-bg/90 px-6 py-3 backdrop-blur-sm">
      <Link href="/" className="text-sm font-bold uppercase tracking-widest text-accent no-underline">
        ★ Showfier
      </Link>

      <div className="flex items-center gap-6 text-xs uppercase tracking-wider">
        <a href="#how-it-works" className="text-muted hover:text-white no-underline">
          How it works
        </a>
        <a href="#pricing" className="text-muted hover:text-white no-underline">
          Pricing
        </a>
        <a href="#faq" className="text-muted hover:text-white no-underline">
          FAQ
        </a>
        <Link href="/login" className="text-muted hover:text-white no-underline">
          Log in
        </Link>
        <Link
          href="/signup"
          className="bg-accent px-3 py-1.5 font-bold text-black no-underline hover:bg-yellow-300"
        >
          Sign up
        </Link>
      </div>
    </nav>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd web && npx vitest run tests/components/Nav.test.tsx
```

Expected: `3 passed`

- [ ] **Step 5: Add Nav to root layout**

Replace `web/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import Nav from "@/components/Nav";
import "./globals.css";

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
});

export const metadata: Metadata = {
  title: "Showfier — Stop Rebuilding Your Shows",
  description:
    "Upload a Yamaha CL/QL show file, download a DiGiCo SD/Quantum translation. 30 seconds.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={jetbrains.variable}>
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 6: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/components/Nav.tsx web/tests/components/Nav.test.tsx web/src/app/layout.tsx
git commit -m "feat: add sticky navigation bar with brand mark and auth links"
```

---

## Task 4: Hero section (HeroDropZone)

**Files:**
- Create: `web/src/components/HeroDropZone.tsx`
- Create: `web/tests/components/HeroDropZone.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/tests/components/HeroDropZone.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import HeroDropZone from "../../src/components/HeroDropZone";

describe("HeroDropZone", () => {
  it("renders the headline", () => {
    render(<HeroDropZone />);
    expect(
      screen.getByText(/stop rebuilding your shows/i)
    ).toBeInTheDocument();
  });

  it("renders the drop zone prompt", () => {
    render(<HeroDropZone />);
    expect(screen.getByText(/drop .cle here/i)).toBeInTheDocument();
  });

  it("renders the translation preview panels", () => {
    render(<HeroDropZone />);
    expect(screen.getByText(/yamaha cl5/i)).toBeInTheDocument();
    expect(screen.getByText(/digico sd12/i)).toBeInTheDocument();
  });

  it("renders channel names in the preview", () => {
    render(<HeroDropZone />);
    expect(screen.getAllByText(/kick/i).length).toBeGreaterThanOrEqual(2);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && npx vitest run tests/components/HeroDropZone.test.tsx
```

Expected: FAIL — `Cannot find module`

- [ ] **Step 3: Implement the HeroDropZone component**

Create `web/src/components/HeroDropZone.tsx`:

```tsx
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
          Stop rebuilding
          <br />
          your shows.
        </h1>
        <p className="mt-3 text-sm text-muted">
          30 seconds. First one free.
        </p>
        <button
          type="button"
          onClick={handleClick}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          className="mt-6 flex flex-1 cursor-pointer flex-col items-center justify-center border-2 border-dashed border-accent bg-surface p-6 text-center transition-colors hover:bg-accent/10"
        >
          <span className="text-sm font-extrabold uppercase tracking-wider text-accent">
            Drop .CLE here
          </span>
          <span className="mt-1 text-xs text-muted">or click to browse</span>
        </button>
      </div>

      {/* Right column: translation preview */}
      <div className="grid grid-cols-[1fr_auto_1fr] gap-2">
        {/* FROM panel */}
        <div className="flex flex-col border border-border bg-surface p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted">
            From
          </p>
          <p className="mt-1 text-sm font-bold">Yamaha CL5</p>
          <div className="mt-3 flex flex-col gap-1">
            {PREVIEW_CHANNELS.map((ch) => (
              <p key={`from-${ch}`} className="text-xs text-white/80">
                · {ch}
              </p>
            ))}
          </div>
        </div>

        {/* Arrow */}
        <div className="flex items-center text-xl font-extrabold text-accent">
          →
        </div>

        {/* TO panel */}
        <div className="flex flex-col border border-accent bg-surface p-4">
          <p className="text-[10px] uppercase tracking-wider text-accent">To</p>
          <p className="mt-1 text-sm font-bold">DiGiCo SD12</p>
          <div className="mt-3 flex flex-col gap-1">
            {PREVIEW_CHANNELS.map((ch) => (
              <p key={`to-${ch}`} className="text-xs text-success">
                ✓ {ch}
              </p>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd web && npx vitest run tests/components/HeroDropZone.test.tsx
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/components/HeroDropZone.tsx web/tests/components/HeroDropZone.test.tsx
git commit -m "feat: add hero section with drop zone and translation preview"
```

---

## Task 5: Landing page body sections

**Files:**
- Create: `web/src/components/HowItWorks.tsx`
- Create: `web/src/components/WhatTranslates.tsx`
- Create: `web/src/components/PricingTeaser.tsx`
- Create: `web/src/components/FAQ.tsx`
- Create: `web/src/components/Footer.tsx`
- Create: `web/tests/components/LandingPage.test.tsx`

- [ ] **Step 1: Write the landing page smoke test**

Create `web/tests/components/LandingPage.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import HowItWorks from "../../src/components/HowItWorks";
import WhatTranslates from "../../src/components/WhatTranslates";
import PricingTeaser from "../../src/components/PricingTeaser";
import FAQ from "../../src/components/FAQ";
import Footer from "../../src/components/Footer";

describe("HowItWorks", () => {
  it("renders the three steps", () => {
    render(<HowItWorks />);
    expect(screen.getByText(/drop/i)).toBeInTheDocument();
    expect(screen.getByText(/translate/i)).toBeInTheDocument();
    expect(screen.getByText(/download/i)).toBeInTheDocument();
  });
});

describe("WhatTranslates", () => {
  it("renders both columns", () => {
    render(<WhatTranslates />);
    expect(screen.getByText(/what translates/i)).toBeInTheDocument();
    expect(screen.getByText(/what doesn't/i)).toBeInTheDocument();
  });
});

describe("PricingTeaser", () => {
  it("renders three tiers", () => {
    render(<PricingTeaser />);
    expect(screen.getByText(/free/i)).toBeInTheDocument();
    expect(screen.getByText(/credits/i)).toBeInTheDocument();
    expect(screen.getByText(/pro/i)).toBeInTheDocument();
  });
});

describe("FAQ", () => {
  it("renders all six questions", () => {
    render(<FAQ />);
    expect(screen.getByText(/safe to load/i)).toBeInTheDocument();
    expect(screen.getByText(/consoles are supported/i)).toBeInTheDocument();
    expect(screen.getByText(/premium rack/i)).toBeInTheDocument();
    expect(screen.getByText(/file stored/i)).toBeInTheDocument();
    expect(screen.getByText(/try it before/i)).toBeInTheDocument();
    expect(screen.getByText(/who built/i)).toBeInTheDocument();
  });
});

describe("Footer", () => {
  it("renders the brand and copyright links", () => {
    render(<Footer />);
    expect(screen.getByText(/showfier/i)).toBeInTheDocument();
    expect(screen.getByText(/privacy/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && npx vitest run tests/components/LandingPage.test.tsx
```

Expected: FAIL — `Cannot find module`

- [ ] **Step 3: Implement HowItWorks**

Create `web/src/components/HowItWorks.tsx`:

```tsx
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
            <div
              key={s.num}
              className="border border-border bg-surface p-6 text-center"
            >
              <p className="text-3xl text-accent">{s.icon}</p>
              <p className="mt-3 text-xs font-extrabold uppercase tracking-wider text-white">
                {s.num}. {s.title}
              </p>
              <p className="mt-2 text-xs leading-relaxed text-muted">
                {s.desc}
              </p>
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
```

- [ ] **Step 4: Implement WhatTranslates**

Create `web/src/components/WhatTranslates.tsx`:

```tsx
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
              <li key={item} className="text-sm text-white/80">
                ✓ {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-extrabold uppercase tracking-wider text-error">
            × What doesn&apos;t
          </h3>
          <ul className="mt-4 flex flex-col gap-2">
            {DOESNT.map((item) => (
              <li key={item} className="text-sm text-white/60">
                × {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Implement PricingTeaser**

Create `web/src/components/PricingTeaser.tsx`:

```tsx
const TIERS = [
  {
    name: "Free",
    price: "$0",
    desc: "1 lifetime translation",
    note: "See what it does",
    highlighted: false,
  },
  {
    name: "Credits",
    price: "$12–90",
    desc: "1–10 translations",
    note: "Pay as you go",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$19/mo",
    desc: "30 translations/month",
    note: "For working engineers",
    highlighted: true,
  },
] as const;

export default function PricingTeaser() {
  return (
    <section id="pricing" className="border-t border-border px-6 py-20">
      <div className="mx-auto max-w-5xl text-center">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">
          Pricing
        </p>
        <h2 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">
          Simple. Honest.
        </h2>

        <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-3">
          {TIERS.map((t) => (
            <div
              key={t.name}
              className={`border p-6 text-center ${
                t.highlighted
                  ? "border-accent bg-accent/5"
                  : "border-border bg-surface"
              }`}
            >
              <p className="text-xs font-bold uppercase tracking-wider text-muted">
                {t.name}
              </p>
              <p className="mt-2 text-2xl font-extrabold text-white">
                {t.price}
              </p>
              <p className="mt-1 text-xs text-muted">{t.desc}</p>
              <p className="mt-4 text-[10px] uppercase tracking-wider text-muted">
                {t.note}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 6: Implement FAQ**

Create `web/src/components/FAQ.tsx`:

```tsx
"use client";

import { useState } from "react";

const QUESTIONS = [
  {
    q: "Is this safe to load into a live console?",
    a: "Always verify the translated file on the target console before the show. Load it, check the patch list, and spot-check EQ and dynamics on key channels. We generate a full translation report showing exactly what transferred and what didn't.",
  },
  {
    q: "What consoles are supported?",
    a: "Yamaha CL/QL and DiGiCo SD/Quantum are supported in both directions. Allen & Heath dLive, Midas PRO, and SSL Live are coming in future updates.",
  },
  {
    q: "My show has Yamaha Premium Rack plugins. Will those translate?",
    a: "No. Brand-specific plugins and custom DSP cannot be translated because they have no equivalent on the target console. These are logged in your translation report so you know exactly what was dropped.",
  },
  {
    q: "Is my file stored anywhere?",
    a: "Uploaded files are stored temporarily to perform the translation and are automatically deleted within 24 hours. We never share or analyze your show files.",
  },
  {
    q: "Can I try it before paying?",
    a: "Yes. Your first translation is completely free — full output file and full report. No credit card required. Just create an account and upload.",
  },
  {
    q: "Who built this?",
    a: "Showfier was built by a touring audio engineer who got tired of rebuilding show files at 4am. This tool exists because we needed it ourselves.",
  },
] as const;

export default function FAQ() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section id="faq" className="border-t border-border px-6 py-20">
      <div className="mx-auto max-w-3xl">
        <p className="text-center text-xs font-bold uppercase tracking-[3px] text-accent">
          FAQ
        </p>
        <h2 className="mt-3 text-center text-2xl font-extrabold uppercase tracking-tight">
          Questions
        </h2>

        <div className="mt-12 flex flex-col gap-2">
          {QUESTIONS.map((item, i) => (
            <div key={i} className="border border-border bg-surface">
              <button
                type="button"
                onClick={() => setOpen(open === i ? null : i)}
                className="flex w-full items-center justify-between px-5 py-4 text-left text-sm font-bold text-white"
              >
                {item.q}
                <span className="ml-4 text-accent">
                  {open === i ? "−" : "+"}
                </span>
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
```

- [ ] **Step 7: Implement Footer**

Create `web/src/components/Footer.tsx`:

```tsx
export default function Footer() {
  return (
    <footer className="border-t border-border px-6 py-10">
      <div className="mx-auto flex max-w-5xl items-center justify-between text-xs text-muted">
        <p>
          <span className="font-bold text-accent">★ Showfier</span> ©{" "}
          {new Date().getFullYear()}
        </p>
        <div className="flex gap-6">
          <a href="#" className="text-muted hover:text-white no-underline">
            Privacy
          </a>
          <a href="#" className="text-muted hover:text-white no-underline">
            Terms
          </a>
          <a href="#" className="text-muted hover:text-white no-underline">
            Contact
          </a>
        </div>
      </div>
    </footer>
  );
}
```

- [ ] **Step 8: Run test to verify it passes**

```bash
cd web && npx vitest run tests/components/LandingPage.test.tsx
```

Expected: `5 passed`

- [ ] **Step 9: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/components/HowItWorks.tsx web/src/components/WhatTranslates.tsx web/src/components/PricingTeaser.tsx web/src/components/FAQ.tsx web/src/components/Footer.tsx web/tests/components/LandingPage.test.tsx
git commit -m "feat: add landing page body sections (how it works, pricing, FAQ, footer)"
```

---

## Task 6: Assemble landing page

**Files:**
- Modify: `web/src/app/page.tsx`
- Create: `web/src/app/translate/page.tsx` (placeholder)
- Create: `web/src/app/dashboard/page.tsx` (placeholder)

- [ ] **Step 1: Wire up the landing page**

Replace `web/src/app/page.tsx`:

```tsx
import HeroDropZone from "@/components/HeroDropZone";
import HowItWorks from "@/components/HowItWorks";
import WhatTranslates from "@/components/WhatTranslates";
import PricingTeaser from "@/components/PricingTeaser";
import FAQ from "@/components/FAQ";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main>
      <HeroDropZone />
      <HowItWorks />
      <WhatTranslates />
      <PricingTeaser />
      <FAQ />
      <Footer />
    </main>
  );
}
```

- [ ] **Step 2: Create translate placeholder page**

Create `web/src/app/translate/page.tsx`:

```tsx
export default function TranslatePage() {
  return (
    <main className="flex min-h-[80vh] flex-col items-center justify-center px-6 text-center">
      <p className="text-xs font-bold uppercase tracking-[3px] text-accent">
        ★ Showfier
      </p>
      <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">
        Translation flow
      </h1>
      <p className="mt-3 text-sm text-muted">
        Coming in Plan 2b — upload, preview, and download will live here.
      </p>
    </main>
  );
}
```

- [ ] **Step 3: Create dashboard placeholder page**

Create `web/src/app/dashboard/page.tsx`:

```tsx
export default function DashboardPage() {
  return (
    <main className="flex min-h-[80vh] flex-col items-center justify-center px-6 text-center">
      <p className="text-xs font-bold uppercase tracking-[3px] text-accent">
        ★ Showfier
      </p>
      <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">
        Dashboard
      </h1>
      <p className="mt-3 text-sm text-muted">
        Coming in Plan 2b — your translations and upload widget will live here.
      </p>
    </main>
  );
}
```

- [ ] **Step 4: Verify the landing page renders locally**

```bash
cd web && npm run dev
```

Open `http://localhost:3000`. Expected: full landing page with nav, hero (drop zone + translation preview), how it works, what translates, pricing, FAQ, and footer. All on a dark background with monospace font.

Click the hero drop zone — should navigate to `/translate` (placeholder page).

Press Ctrl+C to stop.

- [ ] **Step 5: Run all tests**

```bash
cd web && npx vitest run
```

Expected: all tests pass (constants + Nav + HeroDropZone + LandingPage sections)

- [ ] **Step 6: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/app/page.tsx web/src/app/translate/page.tsx web/src/app/dashboard/page.tsx
git commit -m "feat: assemble landing page and add placeholder routes"
```

---

## Task 7: Supabase schema + client setup

**Files:**
- Create: `web/supabase/migrations/001_initial_schema.sql`
- Create: `web/src/lib/supabase/client.ts`
- Create: `web/src/lib/supabase/server.ts`
- Create: `web/src/lib/supabase/middleware.ts`

- [ ] **Step 1: Write the database migration**

Create `web/supabase/migrations/001_initial_schema.sql`:

```sql
-- profiles: extends auth.users
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  free_used boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users can read own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

-- auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- translations: one row per completed translation
create table public.translations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  source_console text not null,
  target_console text not null,
  source_filename text not null,
  source_r2_key text,
  output_r2_key text,
  report_r2_key text,
  channel_count integer not null,
  translated_params text[] not null default '{}',
  approximated_params text[] not null default '{}',
  dropped_params text[] not null default '{}',
  status text not null default 'pending',
  error_message text,
  created_at timestamptz not null default now()
);

alter table public.translations enable row level security;

create policy "Users can read own translations"
  on public.translations for select
  using (auth.uid() = user_id);

-- anonymous_previews: short-lived rows for pre-signup users
create table public.anonymous_previews (
  id uuid primary key default gen_random_uuid(),
  session_token text not null unique,
  source_r2_key text,
  output_r2_key text,
  report_r2_key text,
  channel_count integer,
  translated_params text[] not null default '{}',
  approximated_params text[] not null default '{}',
  dropped_params text[] not null default '{}',
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '1 hour')
);
```

- [ ] **Step 2: Create the browser Supabase client**

Create `web/src/lib/supabase/client.ts`:

```ts
import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
```

- [ ] **Step 3: Create the server Supabase client**

Create `web/src/lib/supabase/server.ts`:

```ts
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // setAll can be called from Server Component — ignore
          }
        },
      },
    }
  );
}
```

- [ ] **Step 4: Create the middleware Supabase helper**

Create `web/src/lib/supabase/middleware.ts`:

```ts
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const protectedPaths = ["/dashboard", "/translations"];
  const isProtected = protectedPaths.some((p) =>
    request.nextUrl.pathname.startsWith(p)
  );

  if (isProtected && !user) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}
```

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/supabase/ web/src/lib/supabase/
git commit -m "feat: add Supabase schema migration and client libraries"
```

---

## Task 8: Signup page

**Files:**
- Create: `web/src/components/SignupForm.tsx`
- Create: `web/src/app/signup/page.tsx`
- Create: `web/tests/components/SignupForm.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/tests/components/SignupForm.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import SignupForm from "../../src/components/SignupForm";

describe("SignupForm", () => {
  it("renders email and password fields", () => {
    render(<SignupForm />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("renders a submit button", () => {
    render(<SignupForm />);
    expect(
      screen.getByRole("button", { name: /create account/i })
    ).toBeInTheDocument();
  });

  it("renders a link to login", () => {
    render(<SignupForm />);
    expect(screen.getByRole("link", { name: /log in/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && npx vitest run tests/components/SignupForm.test.tsx
```

Expected: FAIL — `Cannot find module`

- [ ] **Step 3: Implement SignupForm**

Create `web/src/components/SignupForm.tsx`:

```tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function SignupForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    setLoading(false);

    if (signUpError) {
      setError(signUpError.message);
      return;
    }

    setSuccess(true);
  };

  if (success) {
    return (
      <div className="text-center">
        <p className="text-xl font-bold text-accent">Check your email</p>
        <p className="mt-3 text-sm text-muted">
          We sent a verification link to <strong className="text-white">{email}</strong>.
          Click it to activate your account.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-sm flex-col gap-4">
      <div>
        <label htmlFor="email" className="text-xs font-bold uppercase tracking-wider text-muted">
          Email
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent"
          placeholder="you@example.com"
        />
      </div>

      <div>
        <label htmlFor="password" className="text-xs font-bold uppercase tracking-wider text-muted">
          Password
        </label>
        <input
          id="password"
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent"
          placeholder="Min 8 characters"
        />
      </div>

      {error && (
        <p className="text-xs text-error">{error}</p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="mt-2 bg-accent px-4 py-2.5 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300 disabled:opacity-50"
      >
        {loading ? "Creating..." : "Create account"}
      </button>

      <p className="text-center text-xs text-muted">
        Already have an account?{" "}
        <Link href="/login" className="text-accent">
          Log in
        </Link>
      </p>
    </form>
  );
}
```

- [ ] **Step 4: Create the signup page**

Create `web/src/app/signup/page.tsx`:

```tsx
import SignupForm from "@/components/SignupForm";

export default function SignupPage() {
  return (
    <main className="flex min-h-[80vh] flex-col items-center justify-center px-6">
      <p className="text-xs font-bold uppercase tracking-[3px] text-accent">
        ★ Showfier
      </p>
      <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">
        Create account
      </h1>
      <p className="mt-2 text-sm text-muted">
        First translation is free. No credit card required.
      </p>
      <div className="mt-8">
        <SignupForm />
      </div>
    </main>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd web && npx vitest run tests/components/SignupForm.test.tsx
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/components/SignupForm.tsx web/src/app/signup/page.tsx web/tests/components/SignupForm.test.tsx
git commit -m "feat: add signup page with email + password form"
```

---

## Task 9: Login page

**Files:**
- Create: `web/src/components/LoginForm.tsx`
- Create: `web/src/app/login/page.tsx`
- Create: `web/tests/components/LoginForm.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/tests/components/LoginForm.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import LoginForm from "../../src/components/LoginForm";

describe("LoginForm", () => {
  it("renders email and password fields", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("renders a submit button", () => {
    render(<LoginForm />);
    expect(
      screen.getByRole("button", { name: /log in/i })
    ).toBeInTheDocument();
  });

  it("renders a link to signup", () => {
    render(<LoginForm />);
    expect(
      screen.getByRole("link", { name: /sign up/i })
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && npx vitest run tests/components/LoginForm.test.tsx
```

Expected: FAIL — `Cannot find module`

- [ ] **Step 3: Implement LoginForm**

Create `web/src/components/LoginForm.tsx`:

```tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    setLoading(false);

    if (signInError) {
      setError(signInError.message);
      return;
    }

    router.push("/dashboard");
    router.refresh();
  };

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-sm flex-col gap-4">
      <div>
        <label htmlFor="email" className="text-xs font-bold uppercase tracking-wider text-muted">
          Email
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent"
          placeholder="you@example.com"
        />
      </div>

      <div>
        <label htmlFor="password" className="text-xs font-bold uppercase tracking-wider text-muted">
          Password
        </label>
        <input
          id="password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent"
          placeholder="Your password"
        />
      </div>

      {error && (
        <p className="text-xs text-error">{error}</p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="mt-2 bg-accent px-4 py-2.5 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300 disabled:opacity-50"
      >
        {loading ? "Logging in..." : "Log in"}
      </button>

      <p className="text-center text-xs text-muted">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="text-accent">
          Sign up
        </Link>
      </p>
    </form>
  );
}
```

- [ ] **Step 4: Create the login page**

Create `web/src/app/login/page.tsx`:

```tsx
import LoginForm from "@/components/LoginForm";

export default function LoginPage() {
  return (
    <main className="flex min-h-[80vh] flex-col items-center justify-center px-6">
      <p className="text-xs font-bold uppercase tracking-[3px] text-accent">
        ★ Showfier
      </p>
      <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">
        Log in
      </h1>
      <p className="mt-2 text-sm text-muted">
        Welcome back.
      </p>
      <div className="mt-8">
        <LoginForm />
      </div>
    </main>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd web && npx vitest run tests/components/LoginForm.test.tsx
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/components/LoginForm.tsx web/src/app/login/page.tsx web/tests/components/LoginForm.test.tsx
git commit -m "feat: add login page with email + password form"
```

---

## Task 10: Auth callback + middleware

**Files:**
- Create: `web/src/app/auth/callback/route.ts`
- Create: `web/src/middleware.ts`

- [ ] **Step 1: Create the auth callback route**

Create `web/src/app/auth/callback/route.ts`:

```ts
import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/dashboard";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  return NextResponse.redirect(`${origin}/login?error=auth_callback_failed`);
}
```

- [ ] **Step 2: Create the Next.js middleware**

Create `web/src/middleware.ts`:

```ts
import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  return await updateSession(request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
```

- [ ] **Step 3: Run all tests to confirm nothing breaks**

```bash
cd web && npx vitest run
```

Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/app/auth/ web/src/middleware.ts
git commit -m "feat: add auth callback handler and session middleware"
```

---

## Task 11: Vercel deployment

**Files:**
- No new files needed — Vercel auto-detects Next.js

- [ ] **Step 1: Build locally to verify the app compiles**

```bash
cd web && npm run build
```

Expected: build completes successfully. Warnings about missing env vars are OK — those get set in the Vercel dashboard.

- [ ] **Step 2: Push to GitHub**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git push origin main
```

- [ ] **Step 3: Deploy to Vercel**

1. Go to vercel.com and sign up / log in with GitHub
2. Click "Add New Project" → import the AudioSolutions repository
3. Set the **Root Directory** to `web`
4. Vercel auto-detects Next.js — no build config needed
5. Add environment variables in the Vercel dashboard:
   - `NEXT_PUBLIC_SUPABASE_URL` — from your Supabase project settings → API
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` — from Supabase → API → anon public
   - `SUPABASE_SERVICE_ROLE_KEY` — from Supabase → API → service_role secret
   - `ENGINE_URL` — `https://audiosolutions-production.up.railway.app`
   - `NEXT_PUBLIC_APP_URL` — your Vercel domain (e.g., `https://showfier.vercel.app`)
6. Click Deploy

- [ ] **Step 4: Set up Supabase project**

1. Go to supabase.com → create a new project (name: "showfier")
2. Go to SQL Editor → paste the contents of `web/supabase/migrations/001_initial_schema.sql` → Run
3. Go to Authentication → URL Configuration:
   - Set **Site URL** to your Vercel domain
   - Add `http://localhost:3000/auth/callback` to Redirect URLs
   - Add `https://your-vercel-domain.vercel.app/auth/callback` to Redirect URLs

- [ ] **Step 5: Verify the deployed site**

1. Visit your Vercel URL — the landing page should render fully
2. Click "Sign up" → create an account → check email for verification link
3. Click the verification link → should redirect to `/dashboard` (placeholder)
4. Navigate to the landing page → nav should still show (no auth-dependent nav changes in Plan 2a — those come later)

- [ ] **Step 6: Commit any final adjustments**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add -A && git status
# Only commit if there are changes
git commit -m "chore: post-deployment adjustments" 2>/dev/null || echo "Nothing to commit"
git push origin main
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Next.js 14 App Router + Tailwind dark monospace theme (Task 1)
- ✅ JetBrains Mono font (Task 1)
- ✅ Sticky nav with brand, section links, Login, Sign up (Task 3)
- ✅ Hero section Option 1 — pitch + drop zone + translation preview (Task 4)
- ✅ "How it works" three-step section (Task 5)
- ✅ "What translates" two-column section (Task 5)
- ✅ Pricing teaser — three tiers (Task 5)
- ✅ FAQ — six questions with accordion (Task 5)
- ✅ Footer with brand + links (Task 5)
- ✅ Landing page assembly (Task 6)
- ✅ Supabase schema — profiles, translations, anonymous_previews with RLS (Task 7)
- ✅ Supabase client libraries — browser, server, middleware (Task 7)
- ✅ Signup page with email + password form (Task 8)
- ✅ Login page with email + password form (Task 9)
- ✅ Auth callback handler (Task 10)
- ✅ Protected route middleware for /dashboard and /translations (Task 10)
- ✅ Vercel deployment (Task 11)

**What this plan does NOT cover (Plan 2b):**
- Upload flow (`<UploadFlow>`, `<ConsoleSelector>`, `<TranslationPreview>`)
- Signup wall modal on anonymous download
- Dashboard with upload widget + translation history
- Translation detail page with download links
- R2 file storage integration
- Cleanup cron job
- Preview → signup → claim flow
- `<VerifyBanner>` component
- Auth-dependent nav (showing Dashboard link when logged in)

**Type consistency check:**
- `ConsoleId` type used consistently across constants.ts
- `detectConsole()` and `otherConsole()` signatures match test calls
- Supabase client functions all named `createClient()` with consistent import paths
- All component names match between imports and file names
