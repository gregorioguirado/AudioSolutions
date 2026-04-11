# Showfier Web App & Auth — Design Spec
**Date:** 2026-04-11
**Status:** Approved for implementation planning
**Project:** AudioSolutions / Showfier
**Scope:** Plan 2 of 3 (Web App & Auth). Plan 1 (Translation Engine) is deployed. Plan 3 (Payments & Entitlements) follows.

---

## 1. Product Overview

**Product name:** Showfier

**Tagline:** Stop rebuilding your shows.

**What this plan delivers:** A Next.js web application where live audio engineers upload a Yamaha CL/QL or DiGiCo SD/Quantum show file, see a live translation preview with per-channel status badges, sign up for an account, and download the translated file plus a PDF report — all in under two minutes. First translation is free. Second translation is blocked with a placeholder until Plan 3 (Payments) is built.

**What this plan does NOT deliver:** Payment processing, subscription management, usage counters, abuse prevention, or any Paddle integration. Those are Plan 3.

---

## 2. Architecture

### Stack

| Layer | Tool | Purpose |
|---|---|---|
| Frontend + API routes | Next.js 14 (App Router) on Vercel | Landing page, upload flow, auth, dashboard |
| Auth + database | Supabase (Postgres + GoTrue) | User accounts, translation history, free-used flag |
| File storage | Cloudflare R2 | Source files, translated output files, PDF reports |
| Translation engine | Python FastAPI on Railway | File parsing, normalization, output generation |

### System flow

```
1. User drops file on landing page (anonymous OK)
2. Next.js API route receives file -> uploads to R2 sources bucket
3. Next.js forwards file to Railway engine POST /translate
4. Engine returns ZIP bundle (translated file + PDF report)
5. Next.js extracts bundle -> uploads both files to R2 outputs/reports buckets
6. Next.js returns translation summary (channel list + status) to browser
7. Browser renders TranslationPreview component (channel list with badges)
8. User clicks "Download":
   - If anonymous -> SignupWall modal -> signup -> claim preview -> download
   - If authenticated -> check free_used flag -> download or block with placeholder
9. Translation row recorded in Supabase
```

### Why this split

Next.js is the "smart" layer handling auth, entitlements, and R2 storage. The Railway engine stays pure — no user context, just parse/translate/write. This means the engine is reusable for a future CLI or API product without rewriting.

---

## 3. Visual Direction

### Theme

- **Background:** #0a0a0a (near-black)
- **Text:** #ffffff (white)
- **Accent:** #ffde00 (yellow)
- **Secondary text:** #888888
- **Success:** #34c759 (green)
- **Warning:** #ffcc00 (yellow)
- **Error:** #ff6b6b (red)
- **Typography:** JetBrains Mono / SF Mono / Menlo (monospace stack)
- **Headlines:** uppercase, bold, tight letter-spacing
- **Brand mark:** ★ SHOWFIER (text wordmark — no logo asset needed for MVP)

### Hero layout (Option 1 — "Clean Baseline")

Two-column CSS grid:
- **Left column:** brand mark -> headline ("STOP REBUILDING YOUR SHOWS.") -> sub ("30 seconds. First one free.") -> prominent yellow-bordered drop zone ("DROP .CLE HERE")
- **Right column:** live translation preview showing FROM panel (Yamaha channel names) -> arrow -> TO panel (DiGiCo channel names with green ✓ badges)
- Both columns grid-aligned, equal height

---

## 4. Pages & Routes

| Route | Purpose | Auth required |
|---|---|---|
| `/` | Landing page — hero, "How it works", "What translates", pricing teaser, FAQ, footer | No |
| `/translate` | Upload + preview flow (anonymous OK; signup wall on download) | No |
| `/signup` | Email + password form, triggers Supabase verification email | No |
| `/login` | Email + password login | No |
| `/auth/callback` | Supabase email verification callback handler | No |
| `/dashboard` | Logged-in home — upload widget + recent translations list | Yes |
| `/translations/[id]` | Translation detail — channel list, status badges, download links | Yes |

### Navigation

- **Anonymous:** Logo, How it works, Pricing, FAQ, Login, Sign up (yellow button)
- **Logged-in:** Logo, Dashboard, History, Account dropdown (Settings, Billing — Billing disabled until Plan 3)

### Reusable components

- `<HeroDropZone>` — landing page hero (Option 1 layout)
- `<ConsoleSelector>` — auto-detect from file extension + editable dropdowns
- `<TranslationPreview>` — channel list with colored status badges (green/yellow/red)
- `<UploadFlow>` — orchestrates drop -> upload -> preview -> download (used on `/translate` and `/dashboard`)
- `<SignupWall>` — modal shown at download step for anonymous users
- `<VerifyBanner>` — yellow "verify this on the target console before the show" warning

---

## 5. Landing Page Sections

Top to bottom:

### 5.1 Navigation bar (sticky)
Logo (SHOWFIER ★) · How it works · Pricing · FAQ · Login · Sign up (yellow button)

### 5.2 Hero (Option 1)
Left: brand -> headline -> sub -> drop zone. Right: live translation preview.

### 5.3 "How it works"
Heading: "THREE STEPS. THIRTY SECONDS."
Three cards in a row: 1. DROP (upload file, auto-detect console) -> 2. TRANSLATE (channels, patch, EQ, dynamics mapped) -> 3. DOWNLOAD (translated file + PDF report).
CTA at bottom: "Try it free ->"

### 5.4 What translates
Two columns:
- **"What translates"** — channel names, input patch, HPF frequency, EQ bands, gate/compressor, mix bus routing, VCA assignments
- **"What doesn't"** — brand-specific plugins (Yamaha Premium Rack, etc.), custom DSP, scene/snapshot data

This section manages expectations before the engineer pays.

### 5.5 Social proof placeholder
"Built by touring engineers, for touring engineers." One quote slot for a future testimonial. Can ship empty — just the positioning sentence.

### 5.6 Pricing teaser
Three columns: Free (1 lifetime translation) · Credits ($12-90 for 1-10 translations) · Pro ($19/mo, 30/month). "See full pricing ->" link (disabled until Plan 3 builds the /pricing page).

### 5.7 FAQ
Six questions:
1. Is this safe to load into a live console?
2. What consoles are supported?
3. My show has Yamaha Premium Rack plugins. Will those translate?
4. Is my file stored anywhere?
5. Can I try it before paying?
6. Who built this?

### 5.8 Footer
Logo, copyright, Privacy (link), Terms (link), Contact (link).

---

## 6. Data Model (Supabase Postgres)

### Table: `profiles`
Extends Supabase `auth.users`. One row per user.

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK, references auth.users(id) |
| email | text | not null |
| created_at | timestamptz | default now() |
| free_used | boolean | default false — has the user consumed their free translation? |

### Table: `translations`
One row per completed translation for an authenticated user.

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK, default gen_random_uuid() |
| user_id | uuid | FK -> profiles(id) |
| source_console | text | "yamaha_cl" or "digico_sd" |
| target_console | text | "yamaha_cl" or "digico_sd" |
| source_filename | text | original filename user uploaded |
| source_r2_key | text | R2 object key for source file |
| output_r2_key | text | R2 object key for translated output |
| report_r2_key | text | R2 object key for PDF report |
| channel_count | integer | not null |
| translated_params | text[] | e.g., ["channel_names", "hpf", "eq_bands"] |
| approximated_params | text[] | |
| dropped_params | text[] | |
| status | text | default 'pending' — pending, complete, failed |
| error_message | text | populated if status = failed |
| created_at | timestamptz | default now() |

### Table: `anonymous_previews`
Short-lived rows for pre-signup previews.

| Column | Type | Notes |
|---|---|---|
| id | uuid | PK, default gen_random_uuid() |
| session_token | text | unique, cookie-based, binds preview to browser |
| source_r2_key | text | |
| output_r2_key | text | |
| report_r2_key | text | |
| channel_count | integer | |
| translated_params | text[] | |
| approximated_params | text[] | |
| dropped_params | text[] | |
| created_at | timestamptz | default now() |
| expires_at | timestamptz | 1-hour TTL; row + R2 objects deleted after |

### Row-Level Security (RLS)

- `profiles` — user can read/update their own row only
- `translations` — user can read their own rows only; inserts happen server-side via service role key
- `anonymous_previews` — no RLS; accessed only via Next.js server routes (service role)

### Why three tables

- `profiles.free_used` is the single flag that enforces the first-translation-free rule.
- `translations` is the permanent record for authenticated users (dashboard, re-download).
- `anonymous_previews` is the bridge: when an anonymous user uploads, a preview row is created with a cookie token. On signup + download, the preview row is copied to a real `translations` row tied to their `user_id`, then the preview row is deleted.

---

## 7. File Storage (Cloudflare R2)

### Buckets

| Bucket | Contents | Retention |
|---|---|---|
| `showfier-sources` | Original uploaded files (.cle, .show) | 24h for free/anon; extended in Plan 3 for Pro |
| `showfier-outputs` | Translated output files | Same as sources |
| `showfier-reports` | PDF translation reports | Permanent for authenticated users; 24h for anon |

### Object key convention

`{user_id_or_anon_token}/{translation_id}/{filename}`

Example: `a7f3b2c1-8d4e.../abc123.../translated.show`

### Access pattern

All buckets private. Downloads happen through Next.js API routes that generate short-lived presigned URLs (10 min expiry) after verifying the user owns the translation. No direct public links.

### Cleanup job

Vercel Cron (once daily):
- Delete expired `anonymous_previews` rows AND their R2 objects
- Delete `translations` source/output R2 objects older than the retention window (reports stay permanent for logged-in users)

---

## 8. User Flows

### Flow A: Anonymous first-time visit -> signup -> download

```
1. Land on / -> click "Try It Free" or drop file in hero
2. Auto-redirect to /translate
3. Next.js: create anonymous_previews row with session cookie token
4. Next.js: POST file to Railway engine /translate
5. Engine returns ZIP -> Next.js unpacks -> uploads to R2 -> updates preview row
6. /translate renders channel list with status badges (TranslationPreview)
7. User clicks "Download" -> SignupWall modal opens
8. User enters email + password -> Supabase sends verification email
9. User clicks email link -> /auth/callback -> session established
10. Next.js: copy preview -> new translations row tied to user_id, delete preview
11. Mark profile.free_used = true
12. Redirect to /translations/[id] with download buttons active
```

### Flow B: Logged-in user translates another file

```
1. Land on /dashboard -> see upload widget
2. Drop file -> upload flow runs (user_id known from start)
3. Check: profile.free_used = true AND no Plan 3 entitlement
4. Block with "Coming soon — payments launching soon" placeholder message
```

Plan 2 ships with this placeholder. Plan 3 replaces it with the Paddle paywall.

### Flow C: Logged-in user re-downloads a past translation

```
1. /dashboard -> recent translations list -> click row
2. /translations/[id] renders channel list + download buttons
3. Click download -> Next.js verifies row.user_id = session.user_id
4. Generate presigned R2 URL (10 min) -> browser downloads
```

### Error flows

- Upload > 50MB -> "File too large, 50MB max"
- Engine returns 400 (unsupported console) -> "We couldn't parse this file. Is it a Yamaha CL/QL or DiGiCo SD/Quantum show file?"
- Engine returns 500 -> "Something went wrong on our end. Please try again, and if it keeps failing, drop us a note at support@showfier.com"
- Supabase auth fails -> standard form error messages
- R2 upload fails -> retry once, then fail with support link

---

## 9. Console Auto-Detection

When a user drops a file, `<ConsoleSelector>` reads the file extension:
- `.cle` -> pre-fill source as `yamaha_cl`
- `.show` -> pre-fill source as `digico_sd`

Both source and target dropdowns are always visible and editable. Auto-detection is a convenience, not a gate. The user can override at any time.

Target defaults to the "other" console (if source is yamaha_cl, target defaults to digico_sd, and vice versa).

---

## 10. Testing Strategy

### Unit tests (Vitest)
- Components render correctly (`<TranslationPreview>`, `<ConsoleSelector>`, etc.)
- Auto-detect logic (filename extensions -> console keys)
- Pure utility functions (R2 key generation, status badge mapping, form validators)

### Integration tests (Vitest + mocked Supabase/R2)
- API route handlers (`/api/translate`, `/api/download/[id]`) with mocked clients
- RLS policies enforced (attempt to read another user's translation -> 403)
- Preview -> signup -> claim flow (anonymous row gets properly bound to new user)

### End-to-end tests (Playwright — happy path only)
- Anonymous user: land on / -> upload .cle fixture -> see preview -> sign up -> download
- Logged-in user: land on /dashboard -> upload -> see second-translation block message

### Not testing (deliberate)
- Real Supabase calls (use test project's service role in integration tests)
- Real Railway engine calls (mock — engine has its own 55-test suite)
- Real R2 uploads (mock with aws-sdk-client-mock)
- Visual regression (overkill for MVP)

---

## 11. Environment Variables

| Variable | Scope | Purpose |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Public | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Public | Supabase anon key (RLS-protected) |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only | Admin key for server-side inserts |
| `R2_ACCOUNT_ID` | Server-only | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Server-only | R2 API key |
| `R2_SECRET_ACCESS_KEY` | Server-only | R2 API secret |
| `R2_BUCKET_SOURCES` | Server-only | `showfier-sources` |
| `R2_BUCKET_OUTPUTS` | Server-only | `showfier-outputs` |
| `R2_BUCKET_REPORTS` | Server-only | `showfier-reports` |
| `ENGINE_URL` | Server-only | Railway engine URL |
| `NEXT_PUBLIC_APP_URL` | Public | Canonical site URL for auth email redirects |

All secrets in `.env.local` during development (already gitignored). Production secrets set only via Vercel dashboard. `NEXT_PUBLIC_*` variables are intentionally browser-safe; everything else is server-only.

---

## 12. Out of Scope

### Plan 3 (Payments & Entitlements)
- Paddle integration (subscriptions, credits, checkout)
- Usage counters ("2 of 30 this month")
- Paywall on second translation (Plan 2 shows a placeholder)
- Billing / invoice / subscription management
- FingerprintJS abuse prevention
- Pro plan features (device limits, extended retention, session enforcement)

### Plan 4 or later
- Allen & Heath dLive, Midas PRO, SSL Live console support
- Team plan + team dashboard
- Enterprise / API access
- PIX via Pagar.me (Brazilian market)
- Scene/snapshot translation
- Bulk translation (multiple files at once)
- Mobile-optimized UI (desktop-first — engineers have laptops at FOH)
- Full /pricing detail page (landing page has a teaser; full page comes with Plan 3)
- Brand assets / logo design (ship with text wordmark "SHOWFIER ★")
