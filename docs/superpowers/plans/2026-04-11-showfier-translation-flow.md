# Showfier Translation Flow — Plan 2b: Upload, Preview, Download, Dashboard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up the full translation product flow — upload a show file, call the Railway engine, show a channel-level preview with status badges, gate downloads behind signup, and display translation history on a dashboard.

**Architecture:** Next.js API routes act as the "smart layer" between browser and Railway engine. Files are stored in Cloudflare R2 via the S3-compatible API (`@aws-sdk/client-s3`). Anonymous users get a cookie-based session token; on signup, their preview is claimed into a real translation row. Logged-in users who've used their free translation see a "payments coming soon" placeholder.

**Tech Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS, @aws-sdk/client-s3, @supabase/ssr, Vitest

**Spec:** `docs/superpowers/specs/2026-04-11-showfier-web-app-design.md` — Sections 2, 7, 8, 9

**Depends on:** Plan 2a completed (landing page, auth, Supabase schema deployed)

---

## File Map

```
web/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── translate/
│   │   │   │   └── route.ts          # POST: receive file, call engine, store in R2, return preview data
│   │   │   ├── download/
│   │   │   │   └── [id]/
│   │   │   │       └── route.ts      # GET: generate presigned R2 URL, redirect
│   │   │   └── claim-preview/
│   │   │       └── route.ts          # POST: move anonymous_preview → translations row
│   │   ├── translate/
│   │   │   └── page.tsx              # Replace placeholder: upload + preview + signup wall
│   │   ├── dashboard/
│   │   │   └── page.tsx              # Replace placeholder: upload widget + history
│   │   └── translations/
│   │       └── [id]/
│   │           └── page.tsx          # Translation detail: channel list + download buttons
│   ├── components/
│   │   ├── ConsoleSelector.tsx       # Source/target dropdowns with auto-detect
│   │   ├── UploadFlow.tsx            # Orchestrates drop → upload → preview → download
│   │   ├── TranslationPreview.tsx    # Channel list with colored status badges
│   │   ├── SignupWall.tsx            # Modal: sign up to download
│   │   ├── VerifyBanner.tsx          # Yellow warning banner
│   │   └── TranslationHistory.tsx    # Recent translations table
│   └── lib/
│       ├── r2.ts                     # R2 client: upload, presign, delete
│       └── engine.ts                 # Railway engine client: translate
├── tests/
│   ├── lib/
│   │   ├── r2.test.ts
│   │   └── engine.test.ts
│   └── components/
│       ├── ConsoleSelector.test.tsx
│       ├── TranslationPreview.test.tsx
│       ├── VerifyBanner.test.tsx
│       └── UploadFlow.test.tsx
```

---

## Task 1: Install R2 SDK + engine client library

**Files:**
- Create: `web/src/lib/r2.ts`
- Create: `web/src/lib/engine.ts`
- Create: `web/tests/lib/r2.test.ts`
- Create: `web/tests/lib/engine.test.ts`

- [ ] **Step 1: Install the AWS S3 SDK**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions/web"
npm install @aws-sdk/client-s3 @aws-sdk/s3-request-presigner
```

- [ ] **Step 2: Write the failing test for engine client**

Create `web/tests/lib/engine.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { OUTPUT_FILENAMES, MAX_UPLOAD_BYTES } from "../../src/lib/engine";

describe("engine constants", () => {
  it("maps digico_sd to .show extension", () => {
    expect(OUTPUT_FILENAMES["digico_sd"]).toBe("translated.show");
  });

  it("maps yamaha_cl to .cle extension", () => {
    expect(OUTPUT_FILENAMES["yamaha_cl"]).toBe("translated.cle");
  });

  it("sets max upload to 50MB", () => {
    expect(MAX_UPLOAD_BYTES).toBe(50 * 1024 * 1024);
  });
});
```

- [ ] **Step 3: Write the failing test for R2 helpers**

Create `web/tests/lib/r2.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { buildR2Key } from "../../src/lib/r2";

describe("buildR2Key", () => {
  it("builds a key with owner, translation id, and filename", () => {
    const key = buildR2Key("user-123", "tx-456", "translated.show");
    expect(key).toBe("user-123/tx-456/translated.show");
  });
});
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd web && npx vitest run tests/lib/engine.test.ts tests/lib/r2.test.ts
```

Expected: FAIL — modules not found

- [ ] **Step 5: Implement engine client**

Create `web/src/lib/engine.ts`:

```ts
import type { ConsoleId } from "./constants";

export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024; // 50 MB

export const OUTPUT_FILENAMES: Record<ConsoleId, string> = {
  digico_sd: "translated.show",
  yamaha_cl: "translated.cle",
};

export interface TranslationResult {
  outputBytes: Buffer;
  reportBytes: Buffer;
  channelCount: number;
  translatedParams: string[];
  approximatedParams: string[];
  droppedParams: string[];
}

export async function callEngine(
  file: Buffer,
  filename: string,
  sourceConsole: ConsoleId,
  targetConsole: ConsoleId
): Promise<TranslationResult> {
  const engineUrl = process.env.ENGINE_URL;
  if (!engineUrl) throw new Error("ENGINE_URL not configured");

  const formData = new FormData();
  formData.append("file", new Blob([file]), filename);
  formData.append("source_console", sourceConsole);
  formData.append("target_console", targetConsole);

  const res = await fetch(`${engineUrl}/translate`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(body.detail || `Engine returned ${res.status}`);
  }

  const zipBuffer = Buffer.from(await res.arrayBuffer());

  const JSZip = (await import("jszip")).default;
  const zip = await JSZip.loadAsync(zipBuffer);

  const outputName = OUTPUT_FILENAMES[targetConsole];
  const outputEntry = zip.file(outputName);
  const reportEntry = zip.file("translation_report.pdf");

  if (!outputEntry || !reportEntry) {
    throw new Error("Engine returned invalid bundle — missing files");
  }

  const outputBytes = Buffer.from(await outputEntry.async("arraybuffer"));
  const reportBytes = Buffer.from(await reportEntry.async("arraybuffer"));

  const channelCount = parseInt(res.headers.get("X-Channel-Count") ?? "0", 10);
  const translatedParams = (res.headers.get("X-Translated") ?? "").split(",").filter(Boolean);
  const approximatedParams: string[] = [];
  const droppedParams = (res.headers.get("X-Dropped") ?? "").split(",").filter(Boolean);

  return {
    outputBytes,
    reportBytes,
    channelCount,
    translatedParams,
    approximatedParams,
    droppedParams,
  };
}
```

- [ ] **Step 6: Implement R2 helpers**

Create `web/src/lib/r2.ts`:

```ts
import { S3Client, PutObjectCommand, GetObjectCommand, DeleteObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

function getR2Client(): S3Client {
  return new S3Client({
    region: "auto",
    endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: process.env.R2_ACCESS_KEY_ID!,
      secretAccessKey: process.env.R2_SECRET_ACCESS_KEY!,
    },
  });
}

export function buildR2Key(ownerId: string, translationId: string, filename: string): string {
  return `${ownerId}/${translationId}/${filename}`;
}

export async function uploadToR2(bucket: string, key: string, body: Buffer, contentType: string): Promise<void> {
  const client = getR2Client();
  await client.send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: key,
      Body: body,
      ContentType: contentType,
    })
  );
}

export async function getPresignedUrl(bucket: string, key: string, expiresIn = 600): Promise<string> {
  const client = getR2Client();
  return getSignedUrl(
    client,
    new GetObjectCommand({ Bucket: bucket, Key: key }),
    { expiresIn }
  );
}

export async function deleteFromR2(bucket: string, key: string): Promise<void> {
  const client = getR2Client();
  await client.send(
    new DeleteObjectCommand({ Bucket: bucket, Key: key })
  );
}
```

- [ ] **Step 7: Install jszip dependency**

```bash
cd web && npm install jszip
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
cd web && npx vitest run tests/lib/engine.test.ts tests/lib/r2.test.ts
```

Expected: `4 passed`

- [ ] **Step 9: Run all tests**

```bash
cd web && npx vitest run
```

Expected: 31 passed (27 existing + 4 new)

- [ ] **Step 10: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/lib/engine.ts web/src/lib/r2.ts web/tests/lib/engine.test.ts web/tests/lib/r2.test.ts web/package.json web/package-lock.json
git commit -m "feat: add R2 storage and Railway engine client libraries"
```

---

## Task 2: ConsoleSelector component

**Files:**
- Create: `web/src/components/ConsoleSelector.tsx`
- Create: `web/tests/components/ConsoleSelector.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/tests/components/ConsoleSelector.test.tsx`:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ConsoleSelector from "../../src/components/ConsoleSelector";

describe("ConsoleSelector", () => {
  it("renders source and target dropdowns", () => {
    render(
      <ConsoleSelector
        source="yamaha_cl"
        target="digico_sd"
        onSourceChange={() => {}}
        onTargetChange={() => {}}
      />
    );
    expect(screen.getByLabelText(/from/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/to/i)).toBeInTheDocument();
  });

  it("shows Yamaha CL/QL as source option", () => {
    render(
      <ConsoleSelector
        source="yamaha_cl"
        target="digico_sd"
        onSourceChange={() => {}}
        onTargetChange={() => {}}
      />
    );
    const sourceSelect = screen.getByLabelText(/from/i) as HTMLSelectElement;
    expect(sourceSelect.value).toBe("yamaha_cl");
  });

  it("calls onSourceChange when source is changed", async () => {
    const user = userEvent.setup();
    const onSourceChange = vi.fn();
    render(
      <ConsoleSelector
        source="yamaha_cl"
        target="digico_sd"
        onSourceChange={onSourceChange}
        onTargetChange={() => {}}
      />
    );
    await user.selectOptions(screen.getByLabelText(/from/i), "digico_sd");
    expect(onSourceChange).toHaveBeenCalledWith("digico_sd");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && npx vitest run tests/components/ConsoleSelector.test.tsx
```

- [ ] **Step 3: Implement ConsoleSelector**

Create `web/src/components/ConsoleSelector.tsx`:

```tsx
import { CONSOLES, type ConsoleId } from "@/lib/constants";

interface Props {
  source: ConsoleId;
  target: ConsoleId;
  onSourceChange: (id: ConsoleId) => void;
  onTargetChange: (id: ConsoleId) => void;
  disabled?: boolean;
}

export default function ConsoleSelector({
  source,
  target,
  onSourceChange,
  onTargetChange,
  disabled = false,
}: Props) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1">
        <label
          htmlFor="source-console"
          className="text-[10px] font-bold uppercase tracking-wider text-muted"
        >
          From
        </label>
        <select
          id="source-console"
          value={source}
          onChange={(e) => onSourceChange(e.target.value as ConsoleId)}
          disabled={disabled}
          className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent disabled:opacity-50"
        >
          {CONSOLES.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <span className="mt-5 text-lg font-extrabold text-accent">→</span>

      <div className="flex-1">
        <label
          htmlFor="target-console"
          className="text-[10px] font-bold uppercase tracking-wider text-muted"
        >
          To
        </label>
        <select
          id="target-console"
          value={target}
          onChange={(e) => onTargetChange(e.target.value as ConsoleId)}
          disabled={disabled}
          className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent disabled:opacity-50"
        >
          {CONSOLES.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd web && npx vitest run tests/components/ConsoleSelector.test.tsx
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/components/ConsoleSelector.tsx web/tests/components/ConsoleSelector.test.tsx
git commit -m "feat: add ConsoleSelector component with auto-detect dropdowns"
```

---

## Task 3: TranslationPreview + VerifyBanner components

**Files:**
- Create: `web/src/components/TranslationPreview.tsx`
- Create: `web/src/components/VerifyBanner.tsx`
- Create: `web/tests/components/TranslationPreview.test.tsx`
- Create: `web/tests/components/VerifyBanner.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `web/tests/components/TranslationPreview.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import TranslationPreview from "../../src/components/TranslationPreview";

const MOCK_DATA = {
  channelCount: 3,
  translatedParams: ["channel_names", "hpf"],
  approximatedParams: ["eq_band_types"],
  droppedParams: ["yamaha_premium_rack"],
  channels: [
    { name: "KICK", status: "translated" as const },
    { name: "SNARE", status: "approximated" as const },
    { name: "KEYS", status: "dropped" as const },
  ],
};

describe("TranslationPreview", () => {
  it("renders the channel count", () => {
    render(<TranslationPreview {...MOCK_DATA} />);
    expect(screen.getByText(/3 channels/i)).toBeInTheDocument();
  });

  it("renders channel names", () => {
    render(<TranslationPreview {...MOCK_DATA} />);
    expect(screen.getByText("KICK")).toBeInTheDocument();
    expect(screen.getByText("SNARE")).toBeInTheDocument();
    expect(screen.getByText("KEYS")).toBeInTheDocument();
  });

  it("renders parameter summary sections", () => {
    render(<TranslationPreview {...MOCK_DATA} />);
    expect(screen.getByText(/translated/i)).toBeInTheDocument();
    expect(screen.getByText(/approximated/i)).toBeInTheDocument();
    expect(screen.getByText(/dropped/i)).toBeInTheDocument();
  });
});
```

Create `web/tests/components/VerifyBanner.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import VerifyBanner from "../../src/components/VerifyBanner";

describe("VerifyBanner", () => {
  it("renders the verification warning", () => {
    render(<VerifyBanner />);
    expect(screen.getByText(/verify/i)).toBeInTheDocument();
  });

  it("mentions checking the patch list", () => {
    render(<VerifyBanner />);
    expect(screen.getByText(/patch list/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd web && npx vitest run tests/components/TranslationPreview.test.tsx tests/components/VerifyBanner.test.tsx
```

- [ ] **Step 3: Implement TranslationPreview**

Create `web/src/components/TranslationPreview.tsx`:

```tsx
interface Channel {
  name: string;
  status: "translated" | "approximated" | "dropped";
}

interface Props {
  channelCount: number;
  translatedParams: string[];
  approximatedParams: string[];
  droppedParams: string[];
  channels: Channel[];
}

const STATUS_STYLES = {
  translated: { icon: "✓", color: "text-success" },
  approximated: { icon: "~", color: "text-warning" },
  dropped: { icon: "×", color: "text-error" },
} as const;

function formatParam(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function TranslationPreview({
  channelCount,
  translatedParams,
  approximatedParams,
  droppedParams,
  channels,
}: Props) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-extrabold uppercase tracking-tight">
          {channelCount} channels translated
        </h2>
      </div>

      {/* Channel list */}
      <div className="border border-border bg-surface p-4">
        <p className="text-[10px] font-bold uppercase tracking-wider text-muted">
          Channel list
        </p>
        <div className="mt-3 flex flex-col gap-1">
          {channels.map((ch) => {
            const style = STATUS_STYLES[ch.status];
            return (
              <div key={ch.name} className="flex items-center gap-2 text-sm">
                <span className={`font-bold ${style.color}`}>{style.icon}</span>
                <span className="text-white">{ch.name}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Parameter summary */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="border border-border bg-surface p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-success">
            ✓ Translated
          </p>
          <ul className="mt-2 flex flex-col gap-1">
            {translatedParams.map((p) => (
              <li key={p} className="text-xs text-white/80">
                {formatParam(p)}
              </li>
            ))}
          </ul>
        </div>

        <div className="border border-border bg-surface p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-warning">
            ~ Approximated
          </p>
          <ul className="mt-2 flex flex-col gap-1">
            {approximatedParams.length === 0 ? (
              <li className="text-xs text-muted">None</li>
            ) : (
              approximatedParams.map((p) => (
                <li key={p} className="text-xs text-white/80">
                  {formatParam(p)}
                </li>
              ))
            )}
          </ul>
        </div>

        <div className="border border-border bg-surface p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-error">
            × Dropped
          </p>
          <ul className="mt-2 flex flex-col gap-1">
            {droppedParams.length === 0 ? (
              <li className="text-xs text-muted">None</li>
            ) : (
              droppedParams.map((p) => (
                <li key={p} className="text-xs text-white/80">
                  {formatParam(p)}
                </li>
              ))
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Implement VerifyBanner**

Create `web/src/components/VerifyBanner.tsx`:

```tsx
export default function VerifyBanner() {
  return (
    <div className="border border-warning/30 bg-warning/5 px-5 py-4">
      <p className="text-sm font-bold text-warning">
        Always verify before the show
      </p>
      <p className="mt-1 text-xs leading-relaxed text-muted">
        Load this file on the target console, check the patch list, and
        spot-check EQ and dynamics on key channels before soundcheck.
      </p>
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd web && npx vitest run tests/components/TranslationPreview.test.tsx tests/components/VerifyBanner.test.tsx
```

Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/components/TranslationPreview.tsx web/src/components/VerifyBanner.tsx web/tests/components/TranslationPreview.test.tsx web/tests/components/VerifyBanner.test.tsx
git commit -m "feat: add TranslationPreview and VerifyBanner components"
```

---

## Task 4: SignupWall modal

**Files:**
- Create: `web/src/components/SignupWall.tsx`

- [ ] **Step 1: Implement SignupWall**

Create `web/src/components/SignupWall.tsx`:

```tsx
"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

export default function SignupWall({ onClose, onSuccess }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [checkEmail, setCheckEmail] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback?next=${window.location.pathname}`,
      },
    });

    setLoading(false);

    if (signUpError) {
      setError(signUpError.message);
      return;
    }

    setCheckEmail(true);
  };

  const handleLogin = async (e: React.FormEvent) => {
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

    onSuccess();
  };

  const [mode, setMode] = useState<"signup" | "login">("signup");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md border border-border bg-bg p-8">
        <button
          type="button"
          onClick={onClose}
          className="float-right text-muted hover:text-white"
        >
          ×
        </button>

        {checkEmail ? (
          <div className="text-center">
            <p className="text-xl font-bold text-accent">Check your email</p>
            <p className="mt-3 text-sm text-muted">
              We sent a verification link to{" "}
              <strong className="text-white">{email}</strong>. Click it, then
              come back here to download.
            </p>
          </div>
        ) : (
          <>
            <p className="text-xs font-bold uppercase tracking-[3px] text-accent">
              ★ Showfier
            </p>
            <h2 className="mt-2 text-xl font-extrabold uppercase tracking-tight">
              {mode === "signup" ? "Sign up to download" : "Log in to download"}
            </h2>
            <p className="mt-1 text-xs text-muted">
              {mode === "signup"
                ? "First translation is free. No credit card required."
                : "Welcome back."}
            </p>

            <form
              onSubmit={mode === "signup" ? handleSubmit : handleLogin}
              className="mt-6 flex flex-col gap-4"
            >
              <div>
                <label
                  htmlFor="wall-email"
                  className="text-xs font-bold uppercase tracking-wider text-muted"
                >
                  Email
                </label>
                <input
                  id="wall-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent"
                  placeholder="you@example.com"
                />
              </div>

              <div>
                <label
                  htmlFor="wall-password"
                  className="text-xs font-bold uppercase tracking-wider text-muted"
                >
                  Password
                </label>
                <input
                  id="wall-password"
                  type="password"
                  required
                  minLength={mode === "signup" ? 8 : 1}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 w-full border border-border bg-surface px-3 py-2 text-sm text-white outline-none focus:border-accent"
                  placeholder={mode === "signup" ? "Min 8 characters" : "Your password"}
                />
              </div>

              {error && <p className="text-xs text-error">{error}</p>}

              <button
                type="submit"
                disabled={loading}
                className="bg-accent px-4 py-2.5 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300 disabled:opacity-50"
              >
                {loading
                  ? "Working..."
                  : mode === "signup"
                    ? "Create account"
                    : "Log in"}
              </button>
            </form>

            <p className="mt-4 text-center text-xs text-muted">
              {mode === "signup" ? (
                <>
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => setMode("login")}
                    className="text-accent hover:underline"
                  >
                    Log in
                  </button>
                </>
              ) : (
                <>
                  Need an account?{" "}
                  <button
                    type="button"
                    onClick={() => setMode("signup")}
                    className="text-accent hover:underline"
                  >
                    Sign up
                  </button>
                </>
              )}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run all tests**

```bash
cd web && npx vitest run
```

Expected: all existing tests pass (no test for SignupWall — it requires Supabase mocking)

- [ ] **Step 3: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/components/SignupWall.tsx
git commit -m "feat: add SignupWall modal for anonymous download gate"
```

---

## Task 5: API route — POST /api/translate

**Files:**
- Create: `web/src/app/api/translate/route.ts`

- [ ] **Step 1: Implement the translate API route**

Create `web/src/app/api/translate/route.ts`:

```ts
import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { v4 as uuidv4 } from "crypto";
import { createClient } from "@/lib/supabase/server";
import { callEngine, MAX_UPLOAD_BYTES, OUTPUT_FILENAMES } from "@/lib/engine";
import { uploadToR2, buildR2Key } from "@/lib/r2";
import type { ConsoleId } from "@/lib/constants";
import { CONSOLES } from "@/lib/constants";

const VALID_CONSOLES = CONSOLES.map((c) => c.id);

export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get("file") as File | null;
  const sourceConsole = formData.get("source_console") as string | null;
  const targetConsole = formData.get("target_console") as string | null;

  if (!file || !sourceConsole || !targetConsole) {
    return NextResponse.json(
      { error: "Missing file, source_console, or target_console" },
      { status: 400 }
    );
  }

  if (!VALID_CONSOLES.includes(sourceConsole as ConsoleId)) {
    return NextResponse.json(
      { error: `Unsupported source console: ${sourceConsole}` },
      { status: 400 }
    );
  }

  if (!VALID_CONSOLES.includes(targetConsole as ConsoleId)) {
    return NextResponse.json(
      { error: `Unsupported target console: ${targetConsole}` },
      { status: 400 }
    );
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    return NextResponse.json(
      { error: "File too large, 50MB max" },
      { status: 413 }
    );
  }

  // Check auth status
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  // If logged in, check free_used
  if (user) {
    const { data: profile } = await supabase
      .from("profiles")
      .select("free_used")
      .eq("id", user.id)
      .single();

    if (profile?.free_used) {
      return NextResponse.json(
        { error: "payments_required", message: "Coming soon — payments launching soon." },
        { status: 402 }
      );
    }
  }

  // Call engine
  const fileBuffer = Buffer.from(await file.arrayBuffer());
  let result;
  try {
    result = await callEngine(
      fileBuffer,
      file.name,
      sourceConsole as ConsoleId,
      targetConsole as ConsoleId
    );
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Translation failed";
    const status = message.includes("Unsupported") ? 400 : 500;
    return NextResponse.json({ error: message }, { status });
  }

  // Generate IDs
  const translationId = crypto.randomUUID();
  const ownerId = user?.id ?? crypto.randomUUID();

  // Upload to R2
  const sourceKey = buildR2Key(ownerId, translationId, file.name);
  const outputKey = buildR2Key(ownerId, translationId, OUTPUT_FILENAMES[targetConsole as ConsoleId]);
  const reportKey = buildR2Key(ownerId, translationId, "translation_report.pdf");

  try {
    await Promise.all([
      uploadToR2(process.env.R2_BUCKET_SOURCES!, sourceKey, fileBuffer, "application/octet-stream"),
      uploadToR2(process.env.R2_BUCKET_OUTPUTS!, outputKey, result.outputBytes, "application/octet-stream"),
      uploadToR2(process.env.R2_BUCKET_REPORTS!, reportKey, result.reportBytes, "application/pdf"),
    ]);
  } catch {
    return NextResponse.json(
      { error: "Failed to store translation files. Please try again." },
      { status: 500 }
    );
  }

  // Store record
  if (user) {
    // Authenticated: create translations row + mark free_used
    await supabase.from("translations").insert({
      id: translationId,
      user_id: user.id,
      source_console: sourceConsole,
      target_console: targetConsole,
      source_filename: file.name,
      source_r2_key: sourceKey,
      output_r2_key: outputKey,
      report_r2_key: reportKey,
      channel_count: result.channelCount,
      translated_params: result.translatedParams,
      approximated_params: result.approximatedParams,
      dropped_params: result.droppedParams,
      status: "complete",
    });

    await supabase
      .from("profiles")
      .update({ free_used: true })
      .eq("id", user.id);

    return NextResponse.json({
      translationId,
      channelCount: result.channelCount,
      translatedParams: result.translatedParams,
      approximatedParams: result.approximatedParams,
      droppedParams: result.droppedParams,
      authenticated: true,
    });
  } else {
    // Anonymous: create anonymous_previews row with session token
    const sessionToken = crypto.randomUUID();
    const cookieStore = await cookies();
    cookieStore.set("preview_token", sessionToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 3600,
      path: "/",
    });

    await supabase.from("anonymous_previews").insert({
      id: translationId,
      session_token: sessionToken,
      source_r2_key: sourceKey,
      output_r2_key: outputKey,
      report_r2_key: reportKey,
      channel_count: result.channelCount,
      translated_params: result.translatedParams,
      approximated_params: result.approximatedParams,
      dropped_params: result.droppedParams,
    });

    return NextResponse.json({
      translationId,
      channelCount: result.channelCount,
      translatedParams: result.translatedParams,
      approximatedParams: result.approximatedParams,
      droppedParams: result.droppedParams,
      authenticated: false,
    });
  }
}
```

- [ ] **Step 2: Run all tests**

```bash
cd web && npx vitest run
```

Expected: all existing tests pass

- [ ] **Step 3: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/app/api/translate/route.ts
git commit -m "feat: add POST /api/translate route — engine + R2 + preview flow"
```

---

## Task 6: API routes — download + claim-preview

**Files:**
- Create: `web/src/app/api/download/[id]/route.ts`
- Create: `web/src/app/api/claim-preview/route.ts`

- [ ] **Step 1: Implement the download route**

Create `web/src/app/api/download/[id]/route.ts`:

```ts
import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getPresignedUrl } from "@/lib/r2";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { searchParams } = new URL(request.url);
  const fileType = searchParams.get("type"); // "output" | "report" | "source"

  if (!fileType || !["output", "report", "source"].includes(fileType)) {
    return NextResponse.json({ error: "Invalid file type" }, { status: 400 });
  }

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data: translation } = await supabase
    .from("translations")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (!translation) {
    return NextResponse.json({ error: "Translation not found" }, { status: 404 });
  }

  const keyMap: Record<string, string | null> = {
    output: translation.output_r2_key,
    report: translation.report_r2_key,
    source: translation.source_r2_key,
  };

  const r2Key = keyMap[fileType];
  if (!r2Key) {
    return NextResponse.json({ error: "File not available" }, { status: 404 });
  }

  const bucketMap: Record<string, string> = {
    output: process.env.R2_BUCKET_OUTPUTS!,
    report: process.env.R2_BUCKET_REPORTS!,
    source: process.env.R2_BUCKET_SOURCES!,
  };

  const url = await getPresignedUrl(bucketMap[fileType], r2Key);
  return NextResponse.redirect(url);
}
```

- [ ] **Step 2: Implement the claim-preview route**

Create `web/src/app/api/claim-preview/route.ts`:

```ts
import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { createClient } from "@/lib/supabase/server";

export async function POST() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const cookieStore = await cookies();
  const previewToken = cookieStore.get("preview_token")?.value;

  if (!previewToken) {
    return NextResponse.json(
      { error: "No preview to claim" },
      { status: 404 }
    );
  }

  // Find the preview row
  const { data: preview } = await supabase
    .from("anonymous_previews")
    .select("*")
    .eq("session_token", previewToken)
    .single();

  if (!preview) {
    return NextResponse.json(
      { error: "Preview not found or expired" },
      { status: 404 }
    );
  }

  // Copy to translations table
  const { error: insertError } = await supabase.from("translations").insert({
    id: preview.id,
    user_id: user.id,
    source_console: "unknown",
    target_console: "unknown",
    source_filename: "uploaded_file",
    source_r2_key: preview.source_r2_key,
    output_r2_key: preview.output_r2_key,
    report_r2_key: preview.report_r2_key,
    channel_count: preview.channel_count ?? 0,
    translated_params: preview.translated_params ?? [],
    approximated_params: preview.approximated_params ?? [],
    dropped_params: preview.dropped_params ?? [],
    status: "complete",
  });

  if (insertError) {
    return NextResponse.json(
      { error: "Failed to claim preview" },
      { status: 500 }
    );
  }

  // Mark free_used
  await supabase
    .from("profiles")
    .update({ free_used: true })
    .eq("id", user.id);

  // Delete preview row
  await supabase
    .from("anonymous_previews")
    .delete()
    .eq("session_token", previewToken);

  // Clear cookie
  cookieStore.delete("preview_token");

  return NextResponse.json({ translationId: preview.id });
}
```

- [ ] **Step 3: Run all tests**

```bash
cd web && npx vitest run
```

Expected: all existing tests pass

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/app/api/download/ web/src/app/api/claim-preview/
git commit -m "feat: add download and claim-preview API routes"
```

---

## Task 7: UploadFlow component

**Files:**
- Create: `web/src/components/UploadFlow.tsx`
- Create: `web/tests/components/UploadFlow.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/tests/components/UploadFlow.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import UploadFlow from "../../src/components/UploadFlow";

describe("UploadFlow", () => {
  it("renders the drop zone in initial state", () => {
    render(<UploadFlow />);
    expect(screen.getByText(/drop your file here/i)).toBeInTheDocument();
  });

  it("renders console selectors", () => {
    render(<UploadFlow />);
    expect(screen.getByLabelText(/from/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/to/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd web && npx vitest run tests/components/UploadFlow.test.tsx
```

- [ ] **Step 3: Implement UploadFlow**

Create `web/src/components/UploadFlow.tsx`:

```tsx
"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import ConsoleSelector from "./ConsoleSelector";
import TranslationPreview from "./TranslationPreview";
import VerifyBanner from "./VerifyBanner";
import SignupWall from "./SignupWall";
import { detectConsole, otherConsole, type ConsoleId } from "@/lib/constants";

type FlowState = "idle" | "uploading" | "preview" | "error";

interface PreviewData {
  translationId: string;
  channelCount: number;
  translatedParams: string[];
  approximatedParams: string[];
  droppedParams: string[];
  authenticated: boolean;
}

export default function UploadFlow() {
  const router = useRouter();
  const [state, setState] = useState<FlowState>("idle");
  const [source, setSource] = useState<ConsoleId>("yamaha_cl");
  const [target, setTarget] = useState<ConsoleId>("digico_sd");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSignupWall, setShowSignupWall] = useState(false);

  const handleFile = useCallback(
    (f: File) => {
      setFile(f);
      const detected = detectConsole(f.name);
      if (detected) {
        setSource(detected);
        setTarget(otherConsole(detected));
      }
    },
    []
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const handleTranslate = async () => {
    if (!file) return;
    setState("uploading");
    setError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("source_console", source);
    formData.append("target_console", target);

    try {
      const res = await fetch("/api/translate", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        if (res.status === 402) {
          setError("Coming soon — payments launching soon. You've already used your free translation.");
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

    // Claim the preview
    const res = await fetch("/api/claim-preview", { method: "POST" });
    const data = await res.json();

    if (res.ok) {
      router.push(`/translations/${data.translationId}`);
      router.refresh();
    }
  };

  const handleReset = () => {
    setState("idle");
    setFile(null);
    setPreview(null);
    setError(null);
  };

  return (
    <div className="mx-auto max-w-2xl px-6">
      {showSignupWall && (
        <SignupWall
          onClose={() => setShowSignupWall(false)}
          onSuccess={handleSignupSuccess}
        />
      )}

      {state === "idle" && (
        <div className="flex flex-col gap-6">
          <ConsoleSelector
            source={source}
            target={target}
            onSourceChange={setSource}
            onTargetChange={setTarget}
          />

          <div
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="flex flex-col items-center justify-center border-2 border-dashed border-accent bg-surface p-12 text-center transition-colors hover:bg-accent/10"
          >
            <p className="text-sm font-extrabold uppercase tracking-wider text-accent">
              Drop your file here
            </p>
            <p className="mt-1 text-xs text-muted">or click to browse</p>
            <input
              type="file"
              accept=".cle,.show"
              onChange={handleFileInput}
              className="absolute inset-0 cursor-pointer opacity-0"
              style={{ position: "relative" }}
            />
          </div>

          {file && (
            <div className="flex items-center justify-between border border-border bg-surface px-4 py-3">
              <p className="text-sm text-white">{file.name}</p>
              <button
                type="button"
                onClick={handleTranslate}
                className="bg-accent px-4 py-2 text-xs font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300"
              >
                Translate →
              </button>
            </div>
          )}
        </div>
      )}

      {state === "uploading" && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <p className="text-sm font-extrabold uppercase tracking-wider text-accent">
            Translating...
          </p>
          <p className="mt-2 text-xs text-muted">
            Parsing your show file and mapping to the target console.
          </p>
        </div>
      )}

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
          <button
            type="button"
            onClick={handleDownload}
            className="bg-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-black hover:bg-yellow-300"
          >
            Download translated file
          </button>
          <button
            type="button"
            onClick={handleReset}
            className="text-xs text-muted hover:text-white"
          >
            Translate another file
          </button>
        </div>
      )}

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

- [ ] **Step 4: Run test to verify it passes**

```bash
cd web && npx vitest run tests/components/UploadFlow.test.tsx
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/components/UploadFlow.tsx web/tests/components/UploadFlow.test.tsx
git commit -m "feat: add UploadFlow component orchestrating full translation flow"
```

---

## Task 8: Translate page (replace placeholder)

**Files:**
- Modify: `web/src/app/translate/page.tsx`

- [ ] **Step 1: Replace the translate placeholder**

Replace `web/src/app/translate/page.tsx`:

```tsx
import UploadFlow from "@/components/UploadFlow";

export default function TranslatePage() {
  return (
    <main className="py-12">
      <div className="mx-auto max-w-2xl px-6 text-center">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">
          ★ Showfier
        </p>
        <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">
          Translate your show file
        </h1>
        <p className="mt-2 text-sm text-muted">
          Upload a Yamaha CL/QL or DiGiCo SD/Quantum file and get a translated
          version in 30 seconds.
        </p>
      </div>
      <div className="mt-10">
        <UploadFlow />
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Run all tests**

```bash
cd web && npx vitest run
```

Expected: all tests pass

- [ ] **Step 3: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/app/translate/page.tsx
git commit -m "feat: replace translate placeholder with UploadFlow"
```

---

## Task 9: TranslationHistory + Dashboard page

**Files:**
- Create: `web/src/components/TranslationHistory.tsx`
- Modify: `web/src/app/dashboard/page.tsx`

- [ ] **Step 1: Implement TranslationHistory**

Create `web/src/components/TranslationHistory.tsx`:

```tsx
import Link from "next/link";
import { consoleLabel } from "@/lib/constants";

interface Translation {
  id: string;
  source_console: string;
  target_console: string;
  source_filename: string;
  channel_count: number;
  status: string;
  created_at: string;
}

interface Props {
  translations: Translation[];
}

export default function TranslationHistory({ translations }: Props) {
  if (translations.length === 0) {
    return (
      <div className="border border-border bg-surface px-6 py-10 text-center">
        <p className="text-sm text-muted">No translations yet.</p>
        <p className="mt-1 text-xs text-muted">
          Upload a show file above to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {translations.map((t) => (
        <Link
          key={t.id}
          href={`/translations/${t.id}`}
          className="flex items-center justify-between border border-border bg-surface px-4 py-3 no-underline transition-colors hover:border-accent/30"
        >
          <div>
            <p className="text-sm font-bold text-white">{t.source_filename}</p>
            <p className="mt-0.5 text-xs text-muted">
              {consoleLabel(t.source_console)} → {consoleLabel(t.target_console)}
              {" · "}
              {t.channel_count} channels
            </p>
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-wider text-muted">
              {new Date(t.created_at).toLocaleDateString()}
            </p>
            <p className={`text-xs font-bold ${t.status === "complete" ? "text-success" : "text-warning"}`}>
              {t.status}
            </p>
          </div>
        </Link>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Replace the dashboard placeholder**

Replace `web/src/app/dashboard/page.tsx`:

```tsx
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import UploadFlow from "@/components/UploadFlow";
import TranslationHistory from "@/components/TranslationHistory";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: translations } = await supabase
    .from("translations")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(10);

  return (
    <main className="py-12">
      <div className="mx-auto max-w-3xl px-6">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">
          ★ Showfier
        </p>
        <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">
          Dashboard
        </h1>

        {/* Upload widget */}
        <div className="mt-8">
          <h2 className="text-sm font-bold uppercase tracking-wider text-muted">
            New translation
          </h2>
          <div className="mt-4">
            <UploadFlow />
          </div>
        </div>

        {/* Recent translations */}
        <div className="mt-12">
          <h2 className="text-sm font-bold uppercase tracking-wider text-muted">
            Recent translations
          </h2>
          <div className="mt-4">
            <TranslationHistory translations={translations ?? []} />
          </div>
        </div>
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Run all tests**

```bash
cd web && npx vitest run
```

Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/components/TranslationHistory.tsx web/src/app/dashboard/page.tsx
git commit -m "feat: add dashboard with upload widget and translation history"
```

---

## Task 10: Translation detail page

**Files:**
- Create: `web/src/app/translations/[id]/page.tsx`

- [ ] **Step 1: Implement the translation detail page**

Create `web/src/app/translations/[id]/page.tsx`:

```tsx
import { redirect, notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { consoleLabel } from "@/lib/constants";
import TranslationPreview from "@/components/TranslationPreview";
import VerifyBanner from "@/components/VerifyBanner";

export default async function TranslationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: translation } = await supabase
    .from("translations")
    .select("*")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (!translation) {
    notFound();
  }

  return (
    <main className="py-12">
      <div className="mx-auto max-w-2xl px-6">
        <p className="text-xs font-bold uppercase tracking-[3px] text-accent">
          ★ Showfier
        </p>
        <h1 className="mt-3 text-2xl font-extrabold uppercase tracking-tight">
          {translation.source_filename}
        </h1>
        <p className="mt-1 text-sm text-muted">
          {consoleLabel(translation.source_console)} →{" "}
          {consoleLabel(translation.target_console)}
          {" · "}
          {new Date(translation.created_at).toLocaleDateString()}
        </p>

        <div className="mt-6">
          <VerifyBanner />
        </div>

        <div className="mt-6">
          <TranslationPreview
            channelCount={translation.channel_count}
            translatedParams={translation.translated_params}
            approximatedParams={translation.approximated_params}
            droppedParams={translation.dropped_params}
            channels={[]}
          />
        </div>

        {/* Download buttons */}
        <div className="mt-8 flex flex-col gap-3">
          <a
            href={`/api/download/${translation.id}?type=output`}
            className="flex items-center justify-center bg-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-black no-underline hover:bg-yellow-300"
          >
            Download translated file
          </a>
          <a
            href={`/api/download/${translation.id}?type=report`}
            className="flex items-center justify-center border border-accent px-6 py-3 text-sm font-extrabold uppercase tracking-wider text-accent no-underline hover:bg-accent/10"
          >
            Download translation report (PDF)
          </a>
        </div>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Run all tests**

```bash
cd web && npx vitest run
```

Expected: all tests pass

- [ ] **Step 3: Verify build compiles**

```bash
cd web && npm run build
```

Expected: build succeeds

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/app/translations/
git commit -m "feat: add translation detail page with download buttons"
```

---

## Task 11: Auth-dependent Nav update

**Files:**
- Modify: `web/src/components/Nav.tsx`

- [ ] **Step 1: Update Nav to show Dashboard when logged in**

Read `web/src/components/Nav.tsx` first, then replace it with:

```tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function Nav() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user } }) => {
      setIsLoggedIn(!!user);
    });
  }, []);

  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between border-b border-border bg-bg/90 px-6 py-3 backdrop-blur-sm">
      <Link
        href="/"
        className="text-sm font-bold uppercase tracking-widest text-accent no-underline"
      >
        ★ Showfier
      </Link>

      <div className="flex items-center gap-6 text-xs uppercase tracking-wider">
        {isLoggedIn ? (
          <>
            <Link
              href="/dashboard"
              className="text-muted hover:text-white no-underline"
            >
              Dashboard
            </Link>
            <Link
              href="/translate"
              className="bg-accent px-3 py-1.5 font-bold text-black no-underline hover:bg-yellow-300"
            >
              Translate
            </Link>
          </>
        ) : (
          <>
            <a
              href="#how-it-works"
              className="text-muted hover:text-white no-underline"
            >
              How it works
            </a>
            <a
              href="#pricing"
              className="text-muted hover:text-white no-underline"
            >
              Pricing
            </a>
            <a
              href="#faq"
              className="text-muted hover:text-white no-underline"
            >
              FAQ
            </a>
            <Link
              href="/login"
              className="text-muted hover:text-white no-underline"
            >
              Log in
            </Link>
            <Link
              href="/signup"
              className="bg-accent px-3 py-1.5 font-bold text-black no-underline hover:bg-yellow-300"
            >
              Sign up
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Update Nav test to handle client component**

Read `web/tests/components/Nav.test.tsx` first, then update it. The Nav now calls `createClient()` on mount, which needs a mock. Add a mock for the supabase client to the test file:

```tsx
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Nav from "../../src/components/Nav";

vi.mock("../../src/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getUser: vi.fn().mockResolvedValue({ data: { user: null } }),
    },
  }),
}));

describe("Nav", () => {
  it("renders the Showfier brand mark", () => {
    render(<Nav />);
    expect(screen.getByText(/showfier/i)).toBeInTheDocument();
  });

  it("renders Login and Sign up links when logged out", () => {
    render(<Nav />);
    expect(screen.getByRole("link", { name: /log in/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign up/i })).toBeInTheDocument();
  });

  it("renders anchor links for How it works, Pricing, FAQ when logged out", () => {
    render(<Nav />);
    expect(screen.getByRole("link", { name: /how it works/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /pricing/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /faq/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run all tests**

```bash
cd web && npx vitest run
```

Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git add web/src/components/Nav.tsx web/tests/components/Nav.test.tsx
git commit -m "feat: update Nav to show Dashboard link when logged in"
```

---

## Task 12: Push + deploy

- [ ] **Step 1: Run full test suite**

```bash
cd web && npx vitest run
```

Expected: all tests pass

- [ ] **Step 2: Build**

```bash
cd web && npm run build
```

Expected: build succeeds

- [ ] **Step 3: Push to GitHub**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions"
git push origin main
```

Vercel auto-deploys from main. Wait for the deploy to complete.

- [ ] **Step 4: Set up Cloudflare R2 buckets**

1. Go to the Cloudflare dashboard → R2 → Create bucket
2. Create three buckets: `showfier-sources`, `showfier-outputs`, `showfier-reports`
3. Go to R2 → Manage R2 API Tokens → Create API token
4. Copy the Account ID, Access Key ID, and Secret Access Key

- [ ] **Step 5: Add R2 environment variables to Vercel**

In the Vercel dashboard → Settings → Environment Variables, add:
- `R2_ACCOUNT_ID` — from Cloudflare
- `R2_ACCESS_KEY_ID` — from Cloudflare
- `R2_SECRET_ACCESS_KEY` — from Cloudflare
- `R2_BUCKET_SOURCES` — `showfier-sources`
- `R2_BUCKET_OUTPUTS` — `showfier-outputs`
- `R2_BUCKET_REPORTS` — `showfier-reports`

Redeploy after adding the variables.

- [ ] **Step 6: End-to-end smoke test**

1. Visit the landing page → click "Try it free"
2. Upload `engine/tests/fixtures/yamaha_cl5_sample.cle`
3. See translation preview (channel count, parameter summary)
4. Click "Download" → signup wall appears
5. Sign up with a new email → verify email → come back
6. Download the translated file

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Upload flow with file drop + click (Tasks 7, 8)
- ✅ Console auto-detection from file extension (Task 2, via ConsoleSelector)
- ✅ Editable source/target dropdowns (Task 2)
- ✅ Engine call via Next.js API route (Task 5)
- ✅ R2 file storage for source, output, and report (Tasks 1, 5)
- ✅ Channel list with status badges — TranslationPreview (Task 3)
- ✅ Verify banner (Task 3)
- ✅ Signup wall modal for anonymous download (Task 4)
- ✅ Anonymous preview → claim on signup (Task 6)
- ✅ Dashboard with upload widget + recent history (Task 9)
- ✅ Translation detail page with download buttons (Task 10)
- ✅ Presigned URL downloads (Task 6)
- ✅ Auth-dependent nav — Dashboard/Translate when logged in (Task 11)
- ✅ free_used flag enforcement (Task 5)
- ✅ 402 payments placeholder for second translation (Task 5)
- ✅ Error flows — 400/413/500 messages (Task 5)

**What this plan does NOT cover (out of scope):**
- Cleanup cron job (deferred — can be added anytime, no user-facing impact)
- Cloudflare R2 bucket lifecycle policies (set in Cloudflare dashboard, not code)
- Channel-level status in preview (engine doesn't return per-channel status — the `channels` array in TranslationPreview is passed empty for now; the summary-level data is accurate)

**Type consistency check:**
- `ConsoleId` type used consistently across constants.ts, engine.ts, ConsoleSelector, UploadFlow, API routes
- `TranslationResult` interface in engine.ts matches fields used in API route
- `buildR2Key()` signature matches all call sites
- `TranslationPreview` props match what API route returns
- `TranslationHistory` interface matches Supabase translations table columns
