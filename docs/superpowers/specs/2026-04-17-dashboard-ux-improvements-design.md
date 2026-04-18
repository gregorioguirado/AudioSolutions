# Showfier Dashboard UX Improvements — Design Spec

**Date:** 2026-04-17
**Scope:** Web app UX refresh covering four tightly-related improvements
**Supersedes:** Parts of `2026-04-11-showfier-web-app-design.md` (console selector, dashboard layout, translation history)

---

## 1. Overview

This spec replaces four pieces of the current Showfier web app with a more scalable, information-dense design:

1. **Console selector** — brand → model picker that works for the growing console catalogue (currently 2 brands, planned expansion to 8+ brands and 15+ models).
2. **Dashboard / translate page consolidation** — merge the authenticated dashboard and the translate page into one file-first flow, while keeping a public marketing/landing page.
3. **Translation report inline preview** — show translated/approximated/dropped param summary on every history row, and full detail (channel names included) in a right-side pane.
4. **Timezone-aware timecode** — replace the date-only stamp with a stacked relative + absolute time using the browser-local timezone.

All visuals use the existing Showfier brand system (JetBrains Mono, `#0a0a0a` background, `#111111` surface, `#2a2a2a` border, `#ffde00` accent, flat borders, no shadows).

---

## 2. Console Selector

### 2.1 Purpose

The current selector is two flat dropdowns (source, target) with ~4 hardcoded options. It does not scale to per-model selection and does not communicate compatibility between source and target.

The new selector supports:
- Brand → model hierarchy with search
- Auto-detection of the source console from the uploaded file
- Per-model channel/bus metadata
- A compatibility note comparing source vs target

### 2.2 Component Structure

The selector is composed of two symmetric panels (source and target) laid out side by side. Each panel contains:

- A **brand sidebar** on the left: vertical list of brand names (Yamaha, DiGiCo, Allen & Heath, Midas, SSL Live, …).
- A **model panel** on the right containing:
  - A search input that filters models of the currently-selected brand.
  - A grid of model chips. Each chip shows the model name and its max input-channel count (e.g. `SD12 · 96 ch`).

Below each panel is a **detail card** summarising the selected console:
- Heading: model name
- Subtitle: series · "Source" or "Target"
- Rows: Max channels, Mix buses, File format
- Footer: `✓ Detected from file` (source) or `✓ Supported` (target), or `⚠ Too small` / `⚠ 24 channels will be dropped` when target capacity < source.

Between the two panels is a visual arrow indicating translation direction.

Below the full row of panels + cards is a **compat bar** spanning the width:
- Green `✓ …fits within…` if target max ≥ source channels.
- Red `⚠ …channels X–Y will be dropped…` if target max < source channels, including a suggested alternative.

### 2.3 Layout Rules

The two panels + two detail cards live in a 3-column CSS grid: `[source] [arrow] [target]`. Labels, panels, and cards each occupy one row. The arrow column spans panel + card rows and is vertically centred. Both panels stretch to the same height. Detail cards are aligned bottom with their panel.

### 2.4 Source Auto-Detection

When a file is uploaded, the source panel is **pre-filled** based on the file extension / format:
- `.clf` / `.cle` → Yamaha (model inferred from binary inspection where possible).
- `.show` → DiGiCo (model inferred from container metadata where possible).
- Unknown → panel opens empty, user selects manually.

The source panel's model-area shows a green banner (`✓ Auto-detected · Override`) in place of the search input. Clicking "Override" turns the banner into the standard search + chips (same as the target panel).

### 2.5 Warning States

When the user picks a target whose max-channels is less than the detected source channel count:
- The selected target chip renders in red (`#ff6b6b` text + border).
- The target detail card border turns red.
- The `Max channels` row value is red.
- The card footer switches to `⚠ N channels will be dropped`.
- The full-width compat bar turns red with the exact range (e.g. "channels 49–72 will be dropped") and suggests a larger model.

The user is not blocked — the translation still runs and drops what cannot fit.

### 2.6 Data Model

Console catalogue lives in `web/src/lib/constants.ts` (restructured):

```ts
type ConsoleModel = {
  id: string;              // stable slug, e.g. "yamaha-cl5"
  brand: string;           // "Yamaha"
  series: string;          // "CL Series"
  model: string;           // "CL5"
  maxChannels: number;     // 72
  mixBuses: number;        // 24
  fileFormat: string;      // ".clf"
  supported: boolean;      // whether translation engine supports it
};

type ConsoleBrand = {
  name: string;
  models: ConsoleModel[];
};
```

Translations table gains `source_model` and `target_model` columns (stable slugs) alongside existing `source_console` / `target_console` display strings, so legacy rows still render correctly.

---

## 3. Dashboard (merged translate + dashboard)

### 3.1 Routing

- `/` — public landing page. Retains the existing hero, explainer, and drop zone. No history list. Unauthenticated users land here.
- `/dashboard` — authenticated-only page containing upload + history in one place.
- `/translate` — redirected to `/` or `/dashboard` depending on auth state. Removed as a distinct page.

The public landing page continues to own the SEO surface and the marketing copy.

### 3.2 File-First Flow

The dashboard has two states:

**State A (before file drop):**
- Page header + nav (unchanged).
- `New Translation` section with a single dropzone. No console selector is visible.
- `Recent Translations` section below.

**State B (after a file is dropped):**
- Dropzone is replaced by:
  1. A green `Detect Banner` showing the filename + `✓ Detected: <brand model> — <channels> input channels, <buses> mix buses` + `Override` link.
  2. The full Console Selector (Section 2) with the source panel pre-filled.
  3. Target detail card.
  4. Compat bar.
  5. Full-width `Translate →` button (brand yellow, black text).
- `Recent Translations` stays below, unchanged.

The transition from State A to B happens in place (no route change). Dropping another file or clicking "Cancel / Start Over" resets to State A.

### 3.3 Layout

Stacked single-column layout:

```
[ Nav ]
[ New Translation section   ]
[ Recent Translations list  ]
```

All content is inside a centred container. The container widens to ~860–900px on the dashboard (wider than today's `max-w-2xl` / ~672px) to accommodate the side-by-side source/target selector panels. The dropzone, history list, and landing-page marketing blocks continue to use the same inner width for visual consistency.

On viewports narrower than ~720px, the selector's two panels stack vertically (source on top, target below) with the arrow rotating 90°. The detail cards stack to match.

---

## 4. Translation Report Inline Preview

### 4.1 Purpose

The current history list shows only filename + route + channel count + status + date. Engineers want to see what actually translated, approximated, or dropped — and the channel names — without clicking into a detail page.

### 4.2 Component Structure

The history list uses a **two-pane layout**:

- **Left (list) pane** — flex: 1; shows every translation row. Each row includes:
  - Icon
  - Filename (bold) + route (muted, e.g. "Yamaha CL5 → DiGiCo SD12")
  - **Summary chips row** (always visible): three coloured chips — `✓ 47` (green), `~ 2` (yellow), `× 1` (red). Chips are omitted when their count is zero.
  - Channel count, timestamp, status ("Done") aligned right.

- **Right (detail) pane** — fixed width ~280–300px; border-left separator; background `#0d0d0d`.
  - Header: filename + subtitle (`<source> → <target> · <ch> · <timestamp>`) + close `✕`.
  - Summary chips repeated (with full labels this time).
  - Three sections stacked: `✓ Translated` / `~ Approximated` / `× Dropped`, each with its coloured section label and a list of param names.
  - `Channel Names` section at the bottom: 2-column grid of channel name cells (truncated with ellipsis, with "+N more…" row when list is long).
  - `Download .show` button (brand yellow) at the bottom.

### 4.3 Interaction

- Clicking any row populates the right pane with that translation's detail. The active row gets a left yellow accent border and subtle background highlight.
- Clicking `✕` or clicking the active row again collapses the right pane, and the list uses the full width.
- On viewports narrower than ~720px, the right pane becomes a bottom drawer or stacks below the list. (Exact mobile behaviour outside scope of this spec — to be refined during implementation.)

### 4.4 Data Requirements

Existing Supabase `translations` table already stores:
- `translated_params: text[]`
- `approximated_params: text[]`
- `dropped_params: text[]`

New requirement: persist **channel names** from the translation output. We add a `channel_names: text[]` column to the `translations` table (or store it in a related JSONB column if we anticipate additional per-row report metadata). Names are captured at translation time from the parser output. The right detail pane reads them directly from the row — no on-demand file extraction — so opening a history row is always instant.

### 4.5 Deep Link

Each row remains clickable as a full detail page at `/translations/[id]` for sharing / permalink purposes. The right pane is the in-dashboard shortcut; the full page remains the canonical view.

---

## 5. Timezone-Aware Timecode

### 5.1 Format

Each history row shows a two-line time stack at the right of the row, before the status:

- **Top line** — relative time, bold, white, 12px: `2h ago`, `Yesterday`, `5 days ago`, `3 weeks ago`, etc.
- **Bottom line** — absolute time, 11px, muted gray (`#888`): `Apr 17, 4:35 PM CDT`.

Both lines are right-aligned and use the browser's detected local timezone (via `Intl.DateTimeFormat().resolvedOptions().timeZone` and `toLocaleString` with the `timeZoneName: 'short'` option).

### 5.2 Relative Time Thresholds

- `< 60s` → `Just now`
- `< 60m` → `Nm ago`
- `< 24h` → `Nh ago`
- Same calendar day → current-day rules above
- Yesterday → `Yesterday`
- `< 7 days` → `N days ago`
- `< 4 weeks` → `N weeks ago`
- Older → `N months ago` or `N years ago`

### 5.3 Timezone Handling

- `created_at` is stored as `timestamptz` in Postgres (unchanged).
- Conversion to local time happens client-side only.
- No per-user timezone preference stored — browser is the source of truth.
- If the detected timezone abbreviation is ambiguous or empty (rare), fall back to UTC offset (e.g. `UTC-5`).

### 5.4 Library

Use `date-fns` (already lightweight and tree-shakable) for relative formatting; use native `Intl` APIs for absolute formatting. No Moment.js.

---

## 6. Files Affected

Expected touchpoints:

- `web/src/lib/constants.ts` — restructure CONSOLES array into brand/model hierarchy.
- `web/src/components/ConsoleSelector.tsx` — rewrite to new symmetric panel design.
- `web/src/components/UploadFlow.tsx` — rewire for file-first flow; orchestrate State A / State B.
- `web/src/components/TranslationHistory.tsx` — rewrite for two-pane layout with summary chips + right detail pane.
- `web/src/components/TranslationPreview.tsx` — reused (or refactored) as the content of the right detail pane.
- `web/src/components/Timecode.tsx` — new component for the stacked relative + absolute time.
- `web/src/app/dashboard/page.tsx` — layout orchestration for merged view.
- `web/src/app/translate/page.tsx` — removed or redirected.
- `web/src/app/page.tsx` — confirm landing page retains upload widget for anonymous preview.
- `web/supabase/migrations/` — new migration: add `source_model`, `target_model`, `channel_names` columns.

---

## 7. Out of Scope

Explicitly not addressed in this spec:

- Mobile-specific layout refinements beyond the stated stacking behaviour.
- Real per-model translation differentiation in the engine (engine still treats all SD models the same for now; UI is forward-compatible).
- Search across brands (search inside the target panel filters models within the currently-selected brand only).
- Saved user preferences (remembered target console per session, etc.).
- Batch translations / multi-file upload.

---

## 8. Success Criteria

- A user with a `.clf` file can drop it, see source auto-detected, pick a DiGiCo SD12 target in under three clicks, and click Translate.
- A user with a target that is too small sees an unambiguous red warning telling them which channels will be lost.
- A user browsing their history can see the translated/approx/dropped counts on every row and see full param + channel detail without leaving the page.
- Times shown respect the user's browser timezone and read naturally both at a glance (`2h ago`) and precisely (`Apr 17, 4:35 PM CDT`).
