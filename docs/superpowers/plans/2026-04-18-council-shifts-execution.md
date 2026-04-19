# Council Shifts — Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the 20 shift items from `docs/council/council-driven-shifts-2026-04-18.md` to ship a legally-covered, trust-audited, paying-customer-capable Showfier — then scale to Big Three console coverage.

**Architecture:** Mixed-ownership phased plan. Three task types: **AGENT** (Claude writes code/docs), **USER** (Gregorio does real-world action — legal, financial, console-testing, outreach), **MIXED** (agent drafts, user approves/commits). Phases have explicit gates; within phases, parallelizable tasks are dispatched to subagents simultaneously.

**Tech Stack:** Python 3.12 / FastAPI on Railway · Next.js 14 / TypeScript / Tailwind on Vercel · Supabase (Postgres + GoTrue) · Cloudflare R2 (S3-compatible) · Paddle (to be integrated) · pytest + Vitest for tests.

---

## Context Primer (read this first, fresh session)

A new Claude session picking up this plan needs to know:

1. **Project:** Showfier is a cloud SaaS that translates mixing console show files between brands. MVP (Yamaha CL/QL ↔ DiGiCo SD) is deployed. Web app ~80% complete. Payments not yet integrated.

2. **Source docs (read in this order):**
   - `CLAUDE.md` — project rules (WAT framework, guardrails, user profile)
   - `docs/council/council-driven-shifts-2026-04-18.md` — WHY these 20 steps exist
   - `docs/council/council-report-2026-04-18-1628.html` — the full council verdict
   - `docs/showfier-project-overview-and-market-analysis.md` — the existing plan (to edit)
   - `docs/research/yamaha-clf-format.md` — reference for reverse-engineering other formats
   - `engine/parsers/yamaha_cl_binary.py` — reference parser implementation
   - `engine/models/universal.py` — the canonical ShowFile data model

3. **Repo layout:**
   ```
   engine/             Python FastAPI backend (parsers, writers, translator)
   web/                Next.js frontend
   samples/            Real console files + calibration files
   docs/               All design docs, research, plans
   .env                Secrets (never commit)
   ```

4. **Hard guardrails from CLAUDE.md:**
   - No spending without user approval
   - No secrets in code
   - No publishing/deploying without user approval
   - No modifying workflows/CLAUDE.md without asking
   - No fabricating data

5. **User profile:** Gregorio — deep audio engineering domain expertise, limited software dev background. Explain technical concepts in plain language. Prefers managed-service stacks.

6. **Pre-existing artifacts this plan depends on:**
   - ToS disclaimer copy drafted in `docs/showfier-project-overview-and-market-analysis.md` §14
   - 3-tier pricing direction decided in the shift-log
   - Paddle chosen as payment processor (not Stripe — don't re-litigate)
   - E&O insurance quote estimated at ~$1,100/yr

---

## Phase Map

```
PHASE 0  Gate: DiGiCo validation          [USER + AGENT]   BLOCKS ALL
    ↓
PHASE 1  Legal + Pricing + Commit         [3 parallel tracks]
    ↓
PHASE 2  Payments + Harness + Verify-UX   [3 parallel agents]
    ↓
PHASE 3  Demo + Copy + QL                 [2 agents + 1 user parallel]
    ↓
PHASE 4  Launch                           [USER-sequential]
    ↓
PHASE 5  Scale + MBDF batch-win           [2 parallel agents after user prep]
    ↓
PHASE 6  Doc sync                         [up to 7 parallel agents]
```

Any phase can be handed off to a fresh Claude session at its boundary. Mid-phase handoffs require finishing the current task first.

---

# PHASE 0 — Critical Gate: DiGiCo Validation

**Gate:** Every downstream phase assumes our synthetic DiGiCo XML writer produces a file that at least DiGiCo Offline Software can open. Until this gate passes, do not start Phase 1.

### Task 0.1 — USER validates DiGiCo output in Offline Software

**Owner:** USER (Gregorio)
**Files touched:** none (manual test)
**Depends on:** nothing

- [ ] **Step 1:** Install DiGiCo Offline Software (free from digico.biz) on your laptop.
- [ ] **Step 2:** Run the engine locally: `cd engine && uvicorn app.main:app --reload`
- [ ] **Step 3:** Open a browser to `http://localhost:3000/translate` (run `cd web && npm run dev` first if needed). Upload `samples/Example 1 CL5.CLF`. Select target: DiGiCo SD. Download the output.
- [ ] **Step 4:** Open the downloaded `.show` file in DiGiCo Offline Software. Note: does it load cleanly? Do channel names appear? Are HPF / EQ / fader values preserved?
- [ ] **Step 5:** Write results to `docs/research/digico-validation-report.md` with three sections: (a) what loaded correctly, (b) what was missing or wrong, (c) screenshots of any error dialogs.

**Done when:** `docs/research/digico-validation-report.md` exists with factual observations.

### Task 0.2 — AGENT triages validation report and fixes blockers

**Owner:** AGENT
**Files touched:** depends on findings — likely `engine/writers/digico_sd.py`, possibly `engine/translator.py`
**Depends on:** Task 0.1 complete

- [ ] **Step 1:** Read `docs/research/digico-validation-report.md`.
- [ ] **Step 2:** If the file loaded cleanly with acceptable fidelity → skip to Step 6 (no fix needed; pass the gate).
- [ ] **Step 3:** If the file failed to load or was rejected by Offline: dispatch a focused subagent to diagnose the writer output. Prompt: *"Read `docs/research/digico-validation-report.md`. Read `engine/writers/digico_sd.py`. The current synthetic XML writer produces output that DiGiCo Offline won't open. Diagnose why (likely missing required XML elements, wrong root node name, missing show metadata). Fix `engine/writers/digico_sd.py` and add a pytest fixture that locks the corrected output."*
- [ ] **Step 4:** Review subagent's fix. Run `pytest engine/tests/ -v` and confirm no regressions.
- [ ] **Step 5:** Ask user to re-run Task 0.1 to confirm the fix works.
- [ ] **Step 6:** Commit: `git commit -m "fix: DiGiCo writer output accepted by Offline Software"` (skip commit if no code changed).

**GATE:** Do not start Phase 1 until Task 0.1 results are acceptable AND Task 0.2 commit (if needed) is in.

---

# PHASE 1 — Legal Cover + Pricing Fix + Council Artifacts Committed

Three parallel tracks. Dispatch Tasks 1.1, 1.3, 1.4 as subagents in a single message. Task 1.2 runs on the user's side in parallel.

**Dispatch block (send in one message):**
```
Agent A: Task 1.1 — ToS polish
Agent B: Task 1.3 — Pricing 3-tier fix
Agent C: Task 1.4 — Commit council artifacts
(User runs Task 1.2 in parallel — broker call)
```

### Task 1.1 — AGENT finalizes ToS with liability cap + show-day disclaimer

**Owner:** AGENT (subagent)
**Files:**
- Create: `web/public/legal/terms-of-service.md`
- Create: `web/public/legal/translation-accuracy-disclaimer.md`
- Modify: `web/src/app/layout.tsx` (add footer link to /legal/terms)
- Modify: `web/src/app/translate/page.tsx` (add disclaimer acknowledgment checkbox — blocks download until checked)
**Depends on:** existing ToS copy draft in `docs/showfier-project-overview-and-market-analysis.md` §14

- [ ] **Step 1:** Read §14 of the project-overview doc. Extract the "Translation Accuracy Disclaimer" block verbatim.
- [ ] **Step 2:** Write `web/public/legal/terms-of-service.md` with: as-is disclaimer, professional-use clause, liability cap at fees paid in 12 months, no indirect damages, user indemnification, no format guarantee, Delaware governing law. Use the §14 content as source material; expand into a full ToS structure.
- [ ] **Step 3:** Write `web/public/legal/translation-accuracy-disclaimer.md` with the exact verbatim disclaimer text from §14.
- [ ] **Step 4:** Add footer link to both pages in `web/src/app/layout.tsx`.
- [ ] **Step 5:** In `web/src/app/translate/page.tsx` or wherever the download-translated-file button lives, add a required checkbox: "I understand translations must be verified on the target console before any live performance." Button disabled until checked.
- [ ] **Step 6:** Write a Vitest test confirming the download button is disabled by default and enabled after the checkbox is clicked.
- [ ] **Step 7:** Run `cd web && npm test` — confirm passes.
- [ ] **Step 8:** Commit: `git add web/public/legal/ web/src/app/layout.tsx web/src/app/translate/page.tsx web/src/app/translate/__tests__/ && git commit -m "feat(legal): add ToS, liability disclaimer, and verify-before-doors acknowledgment"`

### Task 1.2 — USER obtains E&O insurance quote

**Owner:** USER (Gregorio)
**Files:** none (real-world task)
**Depends on:** nothing

- [ ] **Step 1:** Contact 2 brokers specializing in Technology E&O for US software businesses (Hiscox, Embroker, or Vouch are common options for SaaS founders).
- [ ] **Step 2:** Request quote for $1M/occurrence Technology E&O policy. Budget expectation: ~$1,100–$1,500/yr.
- [ ] **Step 3:** Select quote, pay premium, save policy PDF to a secure location (NOT the git repo).
- [ ] **Step 4:** Add a private note to `.env.local` or your own records with policy number + expiration date. **Do not commit policy details.**

**Done when:** premium paid and policy active. Tell the agent "E&O active" to unblock Phase 2.

### Task 1.3 — AGENT fixes 7-tier pricing → 3-tier (web + engine)

**Owner:** AGENT (subagent)
**Files:**
- Modify: `web/src/app/pricing/page.tsx` (or wherever the pricing table lives — grep for "Credit Pack" or "$45" to locate)
- Modify: any API endpoint that returns pricing tiers (grep engine/app/ for pricing metadata)
- Modify: `docs/showfier-project-overview-and-market-analysis.md` §6
**Depends on:** nothing

- [ ] **Step 1:** Locate existing pricing page: `grep -r "Credit Pack" web/src/` and `grep -r "45" web/src/app/pricing`.
- [ ] **Step 2:** Write a failing Vitest test: "pricing page renders exactly 3 tiers with labels Free / Pro / Team."
- [ ] **Step 3:** Rewrite the pricing component to render exactly 3 tiers:
  - **Free** — $0 — 1 lifetime translation
  - **Pro** — $19/mo OR $149/yr — unlimited translations
  - **Team** — "Contact for pricing" (no preset) — multi-seat
- [ ] **Step 4:** Remove all references to `$5 single`, `$45 pack of 5`, `$80 pack of 10` from component AND from pricing copy elsewhere (check `web/src/app/page.tsx` homepage hero and FAQ).
- [ ] **Step 5:** If engine has a pricing metadata endpoint (check `engine/app/routes/`), update to match 3 tiers.
- [ ] **Step 6:** Edit `docs/showfier-project-overview-and-market-analysis.md` §6 — replace the 8-row pricing table with the 3-tier table above. Add a one-paragraph note citing the Outsider's critique.
- [ ] **Step 7:** Run `cd web && npm test` — confirm passes.
- [ ] **Step 8:** Commit: `git add web/ engine/app/ docs/showfier-project-overview-and-market-analysis.md && git commit -m "feat(pricing): collapse 8 tiers to 3 — Free/Pro/Team per council Outsider"`

### Task 1.4 — AGENT commits the council artifacts that exist but aren't tracked

**Owner:** AGENT (subagent)
**Files:**
- Existing untracked: `docs/council/council-report-2026-04-18-1628.html`, `docs/council/council-transcript-2026-04-18-1628.md`, `docs/council/council-driven-shifts-2026-04-18.md`
- Existing untracked: `docs/showfier-project-overview-and-market-analysis.md`, `docs/showfier-project-overview-and-market-analysis.html`, `docs/handover/`
- Also: `.superpowers/brainstorm/` should be in `.gitignore`
**Depends on:** nothing

- [ ] **Step 1:** Check `.gitignore` — if it doesn't contain `.superpowers/`, add it.
- [ ] **Step 2:** Stage council docs: `git add docs/council/ docs/showfier-project-overview-and-market-analysis.md docs/showfier-project-overview-and-market-analysis.html docs/handover/ docs/superpowers/plans/2026-04-18-council-shifts-execution.md`
- [ ] **Step 3:** Commit: `git commit -m "docs: add council report, shift-log, market analysis, and execution plan"`
- [ ] **Step 4:** Verify: `git status` — only `.env.local.example` should remain modified (that was intentional from prior work; ignore unless user requests otherwise).

---

# PHASE 2 — Payments + Verification Harness + Verify-Before-Doors UX

**Prerequisite:** Phase 0 gate PASSED (DiGiCo validates) AND Phase 1 Task 1.2 complete (E&O premium paid and USER has said "E&O active").

Three parallel agent tracks. Dispatch Tasks 2.1, 2.2, 2.3 in a single message.

### Task 2.1 — AGENT integrates Paddle

**Owner:** AGENT (subagent)
**Files:**
- Create: `web/src/lib/paddle.ts` (checkout client)
- Create: `web/src/app/api/webhooks/paddle/route.ts` (webhook handler)
- Modify: `web/src/app/dashboard/page.tsx` (add upgrade button)
- Modify: `web/src/lib/supabase/profile.ts` (add subscription_tier field usage)
- Modify: Supabase schema — add `subscription_tier` (text: 'free' | 'pro' | 'team') and `paddle_customer_id` (text) to `profiles` table
- Modify: `web/.env.local.example` (add PADDLE_API_KEY, PADDLE_WEBHOOK_SECRET, PADDLE_PRICE_ID_PRO_MONTHLY, PADDLE_PRICE_ID_PRO_ANNUAL placeholders)
- Test: `web/src/app/api/webhooks/paddle/__tests__/route.test.ts`
**Depends on:** Paddle account exists (USER must confirm before starting — ask: "do you have a Paddle account with products created?")

- [ ] **Step 1:** Ask USER: "Do you have a Paddle sandbox account? Have you created Pro Monthly ($19/mo) and Pro Annual ($149/yr) products in the Paddle dashboard?" If NO → escalate and wait. If YES → proceed. USER should provide the Paddle price IDs.
- [ ] **Step 2:** Add a migration to Supabase schema adding `subscription_tier` and `paddle_customer_id` columns to `profiles`. Use Supabase migration tooling OR apply directly via SQL in the Supabase dashboard (USER applies, agent writes the SQL).
- [ ] **Step 3:** Write failing test `route.test.ts`: webhook endpoint validates signature, transitions user to 'pro' on subscription.created, transitions to 'free' on subscription.cancelled.
- [ ] **Step 4:** Implement webhook handler in `web/src/app/api/webhooks/paddle/route.ts` using Paddle's signature validation.
- [ ] **Step 5:** Run test: `cd web && npx vitest run api/webhooks/paddle` — expect pass.
- [ ] **Step 6:** Build `paddle.ts` checkout client: a single function `openCheckout(priceId, customerEmail)` using Paddle.js.
- [ ] **Step 7:** Add "Upgrade to Pro" button to dashboard when `profile.subscription_tier === 'free'`. Clicking opens Paddle checkout with the monthly price ID.
- [ ] **Step 8:** End-to-end manual test: create two test accounts, run through free tier (1 translation), click upgrade, complete Paddle sandbox checkout, confirm webhook transitions user to 'pro' and unlocks more translations. USER participates in this step.
- [ ] **Step 9:** Commit: `git commit -m "feat(payments): Paddle integration with 3-tier pricing"`

### Task 2.2 — AGENT builds Verification Harness V1

**Owner:** AGENT (subagent)
**Files:**
- Create: `engine/verification/__init__.py`
- Create: `engine/verification/harness.py`
- Create: `engine/verification/round_trip.py`
- Create: `engine/tests/verification/test_harness.py`
- Modify: `engine/translator.py` (add harness hook after every translation)
- Create: `.github/workflows/verification-harness.yml` (CI job — if not using GitHub Actions, skip and run locally)
**Depends on:** nothing (independent of Paddle work)

- [ ] **Step 1:** Write failing test: `test_harness_round_trip_cl_digico_cl_preserves_channel_names` — parse CL5 sample → write DiGiCo XML → parse the DiGiCo XML back → compare channel names.
- [ ] **Step 2:** Create `engine/verification/round_trip.py` with function `round_trip(source_path: Path, target_format: str) -> RoundTripResult`. Returns named tuple with source_show, intermediate_show (after write+re-parse), diff_report.
- [ ] **Step 3:** Create `engine/verification/harness.py` with function `verify_translation(source_show, output_path, target_format) -> HarnessResult`. Re-parses output via the target parser, diffs against source, returns per-parameter pass/fail list.
- [ ] **Step 4:** Implement a fixture-golden pattern: for each calibration file in `samples/`, expected parameter values live in `engine/verification/fixtures/<filename>.yaml`. Harness compares parsed values against fixture values.
- [ ] **Step 5:** Run tests: `cd engine && pytest tests/verification/ -v` — confirm passes.
- [ ] **Step 6:** Add harness hook in `engine/translator.py`: after every translation, call `verify_translation()` and log any failures to a structured log file (do NOT block translation on harness failure — just log).
- [ ] **Step 7:** Create CI workflow (skip if not using GHA — for local-only, add a `make verify` target).
- [ ] **Step 8:** Commit: `git commit -m "feat(verification): round-trip harness with calibration-file fixtures"`

### Task 2.3 — AGENT adds "verify before doors" UX step

**Owner:** AGENT (subagent)
**Files:**
- Modify: `web/src/app/translate/[id]/page.tsx` (translation detail / download page)
- Create: `web/src/components/VerifyBeforeDoorsModal.tsx`
- Test: `web/src/components/__tests__/VerifyBeforeDoorsModal.test.tsx`
**Depends on:** nothing (independent of harness)

- [ ] **Step 1:** Write failing Vitest test: "clicking Download opens VerifyBeforeDoorsModal; modal has checkbox 'I will verify on the target console before any live performance'; Download button inside modal is disabled until checkbox is checked."
- [ ] **Step 2:** Build `VerifyBeforeDoorsModal.tsx` component. Structure: title, body paragraph (rephrase from `docs/showfier-project-overview-and-market-analysis.md` §14 disclaimer), checkbox, two buttons (Cancel / Download).
- [ ] **Step 3:** Wire the modal to the Download button on the translation detail page. Replace direct download behavior with "open modal → check box → then download."
- [ ] **Step 4:** Run tests: `cd web && npm test -- VerifyBeforeDoorsModal` — confirm passes.
- [ ] **Step 5:** Manual verify: upload a file, generate translation, click download → modal opens → button disabled → check box → button enables → click → file downloads.
- [ ] **Step 6:** Commit: `git commit -m "feat(ux): require verify-before-doors acknowledgment before download"`

---

# PHASE 3 — Demo + Copy + QL Validation

Two parallel agent tracks + one user task. Dispatch Tasks 3.1, 3.3 as subagents. Task 3.2 is user-only.

### Task 3.1 — AGENT rewrites landing page copy per Outsider critique

**Owner:** AGENT (subagent), user approves final copy
**Files:**
- Modify: `web/src/app/page.tsx` (homepage)
- Modify: any hero component (`web/src/components/Hero.tsx` if it exists)
**Depends on:** nothing

- [ ] **Step 1:** Read current homepage copy: `cat web/src/app/page.tsx` (or read via Read tool).
- [ ] **Step 2:** Identify and list all current copy strings: hero tagline, sub-tagline, "DROP .CLE HERE", any FAQ mentioning "1 lifetime," etc.
- [ ] **Step 3:** Write replacement copy per Outsider critique:
  - **New hero tagline:** "Switch console brands in 30 seconds, not 8 hours." (replaces "Stop rebuilding your shows.")
  - **New sub-tagline:** "Upload your show file from one mixing console, download it ready for another. First translation free." (replaces "30 seconds. First one free.")
  - **New drop-zone copy:** "Drop a show file here — .CLF, .CLE, or .show" (replaces "DROP .CLE HERE")
  - **Remove "1 lifetime"** anywhere it appears — replace with "1 free translation."
  - **Add one-sentence explainer near the hero:** "Showfier converts show files between Yamaha, DiGiCo, and soon Allen & Heath consoles — so you don't rebuild from scratch when the venue has the wrong brand."
- [ ] **Step 4:** Apply changes via Edit tool.
- [ ] **Step 5:** Run `cd web && npm run dev`. Screenshot the hero area. Ask USER to review and approve or request changes.
- [ ] **Step 6:** If USER requests changes, revise and re-screenshot. If approved:
- [ ] **Step 7:** Commit: `git commit -m "feat(landing): rewrite hero copy per council Outsider — explain .CLE, drop tripwire phrasing"`

### Task 3.2 — USER records Loom demo

**Owner:** USER
**Files:** none (real-world asset)
**Depends on:** Phase 2 complete (Paddle live, harness green, verify-UX live) AND Task 3.1 complete (new copy live)

- [ ] **Step 1:** Open a real CL5 show file you already own (not just the sample).
- [ ] **Step 2:** Start a Loom recording. Keep it under 4 minutes.
- [ ] **Step 3:** Show: (a) the new landing page with clear copy, (b) upload the CL5 file, (c) the translation preview, (d) the verify-before-doors checkbox, (e) download the DiGiCo output, (f) open it in DiGiCo Offline and show channel names + HPF + faders present.
- [ ] **Step 4:** Save the Loom URL. Add it to `docs/marketing/loom-demo-url.md` (single-line file).

**Done when:** Loom link saved and viewable.

### Task 3.3 — AGENT validates CL parser against a Yamaha QL file

**Owner:** AGENT (subagent); USER must provide a QL calibration file
**Files:**
- Create: `samples/ql/QL5 empty calibration.CLF` (USER uploads — shares format with CL)
- Modify: `engine/parsers/yamaha_cl_binary.py` (add QL model detection byte handling at offset 0x08)
- Test: `engine/tests/test_yamaha_ql_parser.py`
**Depends on:** USER produces a QL calibration file per `docs/guides/calibration-file-guide.md` — ask USER to run the calibration workflow using QL Editor.

- [ ] **Step 1:** Ask USER: "Please produce a QL calibration file using QL Editor following `docs/guides/calibration-file-guide.md`. Save as `samples/ql/QL5 empty calibration.CLF`. Tell me when done." → wait.
- [ ] **Step 2:** Once file arrives, write failing test: `test_parse_ql_empty_calibration` — calls `parse_yamaha_cl_binary(samples/ql/QL5 empty calibration.CLF)` and confirms it returns a ShowFile with 64 channels (QL5 has 64, CL has 72).
- [ ] **Step 3:** Run test → observe failure mode. Likely: format ID byte at offset 0x08 is different for QL.
- [ ] **Step 4:** Modify `engine/parsers/yamaha_cl_binary.py` to detect QL via the format ID byte and adjust channel count accordingly.
- [ ] **Step 5:** Run test again → expect pass.
- [ ] **Step 6:** Add QL to the supported consoles dropdown in the web UI.
- [ ] **Step 7:** Commit: `git commit -m "feat(parser): Yamaha QL5 support via shared CL binary format"`

---

# PHASE 4 — Launch (user-sequential)

Entirely USER-owned. Agent monitors and assists with drafting DM templates and post copy if asked.

### Task 4.1 — USER seeds 10 touring-engineer DMs with early access

**Owner:** USER
**Files:** agent drafts a DM template if USER asks
**Depends on:** Phase 3 complete (Loom exists, copy live)

- [ ] **Step 1:** Identify 10 touring engineers from your network who mix on Yamaha or DiGiCo.
- [ ] **Step 2:** (Optional) Ask agent to draft a DM template. Prompt: *"Write a short, warm, first-person DM template I can send to touring-engineer friends offering early access to Showfier. Mention the Loom link, 3 months of Pro free for a testimonial, and ask them to try it on a real show file of theirs."*
- [ ] **Step 3:** Send the DMs. Track responses in a simple spreadsheet or `docs/marketing/early-access-log.md`.

**Done when:** 10 DMs sent.

### Task 4.2 — USER publicly posts Loom demo

**Owner:** USER
**Depends on:** Task 4.1 in flight (some warm-lead responses starting to come in)

- [ ] **Step 1:** Post Loom URL + short context to r/livesound. Mark as flaired "Tool" or "Project." Be transparent: you're the creator, you're a touring engineer, you built this because you hated rebuilding shows.
- [ ] **Step 2:** Post on ProSoundWeb forums in a relevant thread (look for existing "universal show file" discussions to join organically rather than starting fresh).
- [ ] **Step 3:** Share in 2–3 Brazilian pro-audio WhatsApp groups.

**Done when:** posts live in ≥3 venues.

### Task 4.3 — USER DMs commenters + comps Pro-free for 3 months in exchange for testimonial

**Owner:** USER
**Depends on:** Task 4.2 has comments/replies

- [ ] **Step 1:** Respond to every comment on your posts.
- [ ] **Step 2:** DM anyone who expresses interest or asks a question. Offer 3 months Pro free for (a) testing on a real file, (b) sharing a short testimonial, (c) one referral.
- [ ] **Step 3:** Manually apply free-Pro comps via a Supabase admin query or an `ADMIN_EMAILS` env var bypass (already exists per `engine/.env.example`).

**Done when:** at least 5 testimonials captured OR at least 3 paying customers (whichever first).

### Task 4.4 — USER starts the Friday discovery sidecar

**Owner:** USER (ongoing, 1 hr/week)
**Depends on:** Task 4.2 live

- [ ] **Step 1:** Schedule one 30-minute call per week with either a rental-company contact OR a touring engineer OR a production manager.
- [ ] **Step 2:** Three questions per call: (a) how often does the wrong-console problem hit you? (b) what would you pay to skip it? (c) if I built a rental-company version of Showfier, what would it need?
- [ ] **Step 3:** Log each call in `docs/discovery/fridaysidecar-log.md` — one entry per call, three bullet points of answers.

**Done when:** 4 entries in the sidecar log (first month). Continues indefinitely.

---

# PHASE 5 — Scale stabilization + MBDF Batch-Win

Three sub-phases: (A) user prep, (B) two parallel agent tracks for MBDF + CL-binary-writer, (C) integration.

### Task 5.1 — USER produces DM7 calibration file set

**Owner:** USER
**Files:** `samples/dm7/DM7 {calibration-type}.dm7f` × 7 files per `docs/guides/calibration-file-guide.md`
**Depends on:** Phase 4 in flight (or running independently if user wants to parallelize)

- [ ] **Step 1:** Install DM7 Editor from Yamaha's website.
- [ ] **Step 2:** Follow `docs/guides/calibration-file-guide.md` and produce the standard 7-file set for DM7: empty, HPF-EQ, dynamics, fader-pan-mute, mix-sends, names-colors, DCA-groups.
- [ ] **Step 3:** Save all files to `samples/dm7/` with the naming convention in the guide.
- [ ] **Step 4:** Confirm with agent: "DM7 calibration files ready" to unblock Task 5.2.

**Done when:** `samples/dm7/` contains 7 calibration files.

### Task 5.2 — AGENT reverse-engineers MBDF container + DM7 parser

**Owner:** AGENT (subagent) — parallel with Task 5.3
**Files:**
- Create: `docs/research/yamaha-mbdf-format.md`
- Create: `engine/parsers/yamaha_mbdf.py`
- Create: `engine/tests/test_yamaha_mbdf_parser.py`
- Modify: `engine/translator.py` (register DM7/TF/RIVAGE format detection)
- Modify: `engine/models/universal.py` only if MBDF needs new fields (flag and ask USER first)
**Depends on:** Task 5.1 complete + Phase 2 harness green (harness will auto-test the new parser)

- [ ] **Step 1:** Dispatch a reverse-engineering subagent with this prompt: *"Read `docs/research/yamaha-clf-format.md` as reference. Read `engine/parsers/yamaha_cl_binary.py` as implementation template. Read `docs/plans/multi-console-expansion.md` §Family B (MBDF) for the existing hypothesis. Files in `samples/dm7/` are 7 DM7 calibration files produced via the diffing method. Reverse-engineer the MBDF container format: identify the header structure, find the `#MMS FIE` section markers, map DM7 parameter offsets by diffing calibration files against the empty baseline. Deliverables: (a) `docs/research/yamaha-mbdf-format.md` with full format spec, (b) `engine/parsers/yamaha_mbdf.py` with `parse_yamaha_mbdf(path: Path) -> ShowFile` function, (c) pytest tests validating against the 7 calibration files."*
- [ ] **Step 2:** Review subagent deliverables. Run harness: `cd engine && pytest tests/verification/ tests/test_yamaha_mbdf_parser.py -v`.
- [ ] **Step 3:** Integrate DM7 format detection into `engine/translator.py` — auto-detect `.dm7f` extension → route to MBDF parser.
- [ ] **Step 4:** Once DM7 works, dispatch two more subagents IN PARALLEL to adapt for TF (`.tff` files) and RIVAGE PM (`.RIVAGEPM` files). Each gets the DM7 parser as reference + the relevant real show file from `samples/`.
- [ ] **Step 5:** Commit after each parser lands: `git commit -m "feat(parser): Yamaha DM7 via MBDF container (from council Phase 5)"`, then TF, then RIVAGE.

### Task 5.3 — AGENT builds template-based CL binary writer

**Owner:** AGENT (subagent) — parallel with Task 5.2
**Files:**
- Create: `engine/writers/yamaha_cl_binary.py`
- Create: `engine/writers/templates/cl5_empty.CLF` (copy from samples)
- Create: `engine/tests/test_yamaha_cl_binary_writer.py`
**Depends on:** nothing (independent of MBDF work — both can run in parallel)

- [ ] **Step 1:** Copy an empty CL5 calibration file from `samples/` to `engine/writers/templates/cl5_empty.CLF` as the write template.
- [ ] **Step 2:** Write failing test: `test_write_cl_binary_preserves_channel_names` — take a ShowFile with named channels → write → re-parse with existing CL binary parser → assert names preserved.
- [ ] **Step 3:** Implement `write_yamaha_cl_binary(show: ShowFile) -> bytes` using the template-based pattern from `docs/plans/multi-console-expansion.md` §6. Load template → overwrite parameter bytes at known offsets (from `docs/research/yamaha-clf-format.md`) → return bytes.
- [ ] **Step 4:** Iterate through: channel names → HPF → EQ → dynamics → fader/pan/mute → mix sends → DCA assignments. One test per parameter class.
- [ ] **Step 5:** Run harness across sample files: every Yamaha parser should round-trip through the new writer.
- [ ] **Step 6:** Register the writer in `engine/translator.py` for target format `yamaha_cl_binary`.
- [ ] **Step 7:** Commit: `git commit -m "feat(writer): template-based Yamaha CL binary writer"`

---

# PHASE 6 — Doc Sync + Roadmap Cleanup

Up to 7 parallel agent subagents, one per affected § of the project-overview doc. Dispatch all in a single message.

**Source doc to edit:** `docs/showfier-project-overview-and-market-analysis.md`
**Driver:** `docs/council/council-driven-shifts-2026-04-18.md`

**Dispatch block (send as one message with 7 parallel Agent calls):**

### Task 6.1 — AGENT edits §6 Business Model & Pricing

- [ ] **Step 1:** Replace the 8-row pricing table with the 3-tier table from the shift-log §POSITIONING SHIFT > Pricing.
- [ ] **Step 2:** Add a one-paragraph note above the table citing the Outsider's critique (5-pack-more-than-singles bug; 7 tiers were decision paralysis).
- [ ] **Step 3:** Keep the pricing justification paragraphs but remove references to the killed tiers.

### Task 6.2 — AGENT edits §8 Go-to-Market Strategy

- [ ] **Step 1:** Demote "Trade Show Demos" from Tier 2 to a new "Deferred" section with a note: "Not pursued until MRR > $2K. Reason: cost-time-benefit doesn't justify at solo-founder pre-revenue stage (council Executor)."
- [ ] **Step 2:** Add "Friday Discovery Sidecar" as a new Tier 1 channel, explaining the 1 hr/week cadence and linking to the shift-log.
- [ ] **Step 3:** Promote "Brazilian WhatsApp groups" to explicit inclusion under Tier 1 "Forum Seeding."

### Task 6.3 — AGENT edits §9 Product Roadmap

- [ ] **Step 1:** Strike all items under Phase 3, Phase 4, Phase 5 that appear in the shift-log §KILL list.
- [ ] **Step 2:** Insert new **Phase 2a: Verification Harness** cornerstone with three sub-items: round-trip CI, calibration-file fixtures, harness hook in translator.
- [ ] **Step 3:** In the Phase 2 list, replace "Add Allen & Heath dLive and Avid VENUE S6L" with "Yamaha QL validation (near-zero effort, shares CL format)". Move A&H dLive to Phase 3.
- [ ] **Step 4:** Add explicit note after the strike-outs: "Items removed per 2026-04-18 council — see `docs/council/council-driven-shifts-2026-04-18.md`."

### Task 6.4 — AGENT edits §10 Console Support Priority

- [ ] **Step 1:** Reorder the priority list:
  1. ✅ Yamaha CL/QL (done)
  2. ✅ DiGiCo SD/Quantum (synthetic writer; real-file parser later)
  3. **NEW priority 1** — Yamaha QL validation (shares CL format)
  4. Yamaha DM7 (MBDF batch-win start)
  5. Yamaha TF (MBDF adaptation)
  6. Yamaha RIVAGE PM (MBDF adaptation)
  7. DiGiCo real .show file parser
  8. Allen & Heath dLive (demoted from priority #1)
  9. Everything else — moved to "Deferred Indefinitely" section
- [ ] **Step 2:** Add rationale paragraph: "Council Executor recommended validating one pair on real traffic before adding consoles. MBDF batch-win prioritized because DM7 + TF + RIVAGE share container format — one parser project unlocks three consoles."

### Task 6.5 — AGENT edits §12 Risk Matrix

- [ ] **Step 1:** Elevate "DiGiCo writer not validated on real console" to near-term risk #1 with likelihood 5 / impact 5 / score 25.
- [ ] **Step 2:** Add new risk: **"Liability / show-day failure mode"** — likelihood 3, impact 5, score 15. Mitigation stack: E&O $1M/occurrence policy, ToS with liability cap, verify-before-doors UX acknowledgment, round-trip verification harness.
- [ ] **Step 3:** Renumber all risks to reflect new ordering.

### Task 6.6 — AGENT edits §14 Policies & Compliance

- [ ] **Step 1:** Change opening framing to: "E&O insurance premium paid and ToS with liability cap live BEFORE Paddle accepts the first charge. This is a hard gate."
- [ ] **Step 2:** Reference the new routes: `web/public/legal/terms-of-service.md` and `web/public/legal/translation-accuracy-disclaimer.md`.
- [ ] **Step 3:** Update "Translation Accuracy Disclaimer" block to exactly match the text now living at `web/public/legal/translation-accuracy-disclaimer.md`.

### Task 6.7 — AGENT edits §16 Strategic Recommendations

- [ ] **Step 1:** Reorder "The Five Things That Matter Most" to:
  1. Validate DiGiCo writer on a real console or via DiGiCo Offline Software.
  2. Ship legal cover (E&O + ToS + verify-before-doors UX) before Paddle.
  3. Build the round-trip verification harness as continuous trust artifact.
  4. MBDF batch-win (DM7 + TF + RIVAGE in one reverse-engineering project).
  5. A&H dLive only after DiGiCo is proven on real paying-customer traffic.
- [ ] **Step 2:** Update "What NOT to Do" list — add: "Don't pursue the $200M Audiotonix exit / Universal Schema play before hitting 100 paying customers (council Expansionist rejected as near-term driver)."
- [ ] **Step 3:** Replace the existing "Month 1–3 / 3–5 / etc." sequence block with a pointer to `docs/superpowers/plans/2026-04-18-council-shifts-execution.md`.

### Task 6.8 — AGENT final commit of doc edits

- [ ] **Step 1:** After all Tasks 6.1–6.7 subagents return, review the combined diff in `docs/showfier-project-overview-and-market-analysis.md`.
- [ ] **Step 2:** Regenerate the HTML version if the existing `.html` sibling is still in use: `pandoc docs/showfier-project-overview-and-market-analysis.md -o docs/showfier-project-overview-and-market-analysis.html` (or equivalent).
- [ ] **Step 3:** Commit: `git commit -m "docs: sync project-overview with council-driven shifts across §6/§8/§9/§10/§12/§14/§16"`

---

# Multi-Agent Dispatch Summary

| Phase | Parallel agents | Can dispatch simultaneously |
|---|---|---|
| Phase 1 | 3 (ToS + Pricing + Commit) | Yes |
| Phase 2 | 3 (Paddle + Harness + Verify-UX) | Yes |
| Phase 3 | 2 agents (Copy + QL) + 1 user task | Yes |
| Phase 5.2 | 3 (DM7 → TF + RIVAGE after DM7 lands) | TF + RIVAGE after DM7 |
| Phase 5.3 | 1 (CL binary writer) | Parallel with 5.2 |
| Phase 6 | Up to 7 (one per § edit) | Yes |

**Not parallelizable:**
- Phase 0 (gate)
- Phase 4 (user sequential)
- Task 2.1 steps within itself (they build on each other)
- Inter-phase order (each phase depends on the previous)

---

# User-Dependent Checkpoints (flag these explicitly to USER)

| Checkpoint | What USER must do | Unblocks |
|---|---|---|
| **Phase 0** | Validate DiGiCo output in Offline Software | Everything downstream |
| **Task 1.2** | E&O broker call + premium payment | Phase 2 start |
| **Task 2.1 pre-start** | Paddle sandbox account + products created + price IDs shared | Paddle integration |
| **Task 3.2** | Record Loom demo | Phase 4 launch |
| **Task 3.3 pre-start** | Produce QL calibration file | QL parser validation |
| **Task 4.1–4.4** | All user-owned outreach work | Phase 5 optional scale work |
| **Task 5.1** | Produce DM7 calibration file set (7 files) | MBDF reverse-engineering |

When handing off to a fresh Claude session: always read `docs/council/council-driven-shifts-2026-04-18.md` first, then this plan. Each phase can be started independently if prior phases show as "complete" in git history (check for commits with messages cited above).

---

# Self-Review Notes

**Spec coverage — all 20 shift-log items mapped:**

1. Validate DiGiCo → Task 0.1 + 0.2
2. Fix pricing to 3 tiers → Task 1.3
3. ToS polish → Task 1.1
4. E&O quote → Task 1.2
5. Paddle integration → Task 2.1
6. Verification harness → Task 2.2
7. Verify-before-doors UX → Task 2.3 (+ partial in 1.1)
8. Landing copy rewrite → Task 3.1
9. Record Loom demo → Task 3.2
10. QL validation → Task 3.3
11. 10-DM seeding → Task 4.1
12. Public post → Task 4.2
13. DM commenters + comp → Task 4.3
14. Friday sidecar → Task 4.4
15. DM7 calibration files → Task 5.1
16. MBDF reverse-engineering → Task 5.2
17. CL binary writer → Task 5.3
18. Edit §6/8/9/10/12/14/16 → Tasks 6.1–6.7
19. Kill from roadmap → covered in Task 6.3 (§9 edit)
20. Commit council artifacts → Task 1.4

All 20 mapped.

**Placeholder scan:** No TBDs, no "add appropriate error handling," no "write tests for the above." Each code step has concrete commands or file paths.

**Type consistency:** ShowFile / parse_yamaha_cl_binary / parse_yamaha_mbdf / write_yamaha_cl_binary / verify_translation — names used consistently across tasks.

---

# Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-18-council-shifts-execution.md`.

Two execution options when ready:

1. **Subagent-Driven (recommended)** — Fresh subagent per task, two-stage review between tasks, fast iteration on independent pieces. Works especially well for Phase 1 (3-parallel), Phase 2 (3-parallel), Phase 5.2 (MBDF batch), and Phase 6 (7-parallel doc edits).

2. **Inline Execution** — Execute tasks in the same session using `superpowers:executing-plans`, with batch checkpoints between phases.

When the next session starts, invoke either skill and reference this plan file as the source of truth.
