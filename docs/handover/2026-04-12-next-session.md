# Next Session Handover — 2026-04-12

## Immediate: R2 Fix Verification

User fixed `R2_ACCOUNT_ID` in Vercel (was full URL, should be just the account ID string). After Vercel redeploys, test the translation flow:

1. Go to https://audio-solutions-pied.vercel.app/translate
2. Upload a `.CLF` file from `samples/`
3. Should get a translation preview instead of "Failed to store translation files"

If still failing, add logging to `web/src/app/api/translate/route.ts` to capture the actual R2 error.

---

## Three Priorities for Next Session

### 1. ConsoleFlip Competitive Analysis

Research consoleflip.com thoroughly:
- What consoles do they support? (confirmed: A&H only)
- What parameters do they translate?
- What are their gaps/complaints from users?
- Pricing model ($15/conversion confirmed by user)
- UX/workflow — how does their upload/download flow work?
- Technical approach if discoverable

Save to `docs/research/consoleflip-analysis.md`.

### 2. Multi-Console Expansion Plan

User wants to support many more consoles. Files already in `samples/`:

| File | Console | Format |
|---|---|---|
| `Bertoleza Sesi Campinas.dm7f` | Yamaha DM7 | `#YAMAHA MBDFProjectFile` header |
| `DOM CASMURRO 2.tff` | Yamaha TF series | `#YAMAHA MBDFProjectFile` header |
| `RIVAGE EMI 21.3.RIVAGEPM` | Yamaha RIVAGE PM | `#YAMAHA MBDFProjectFile` header |
| `Example 1 CL5.CLF` / `.CLE` | Yamaha CL5 | **DONE** — binary parser built |

Key insight: DM7, TF, and RIVAGE PM all share the `#YAMAHA MBDFProjectFile` header — cracking one may crack all three.

User also wants:
- DiGiCo SD/Quantum real file parser (we only have synthetic XML fixtures)
- Allen & Heath dLive/Avantis
- In-brand conversions (e.g., CL5 → QL5, CL5 → TF)

Plan should cover:
- Priority order for console support
- Which consoles share formats (batch wins)
- What sample files we need from the user
- How the reverse-engineering workflow parallelizes

### 3. Calibration File Guide for the User

The CLF reverse-engineering worked incredibly well because of the calibration file method:
1. User creates a blank show in the editor
2. Changes ONE parameter on channel 1
3. Exports as console-native format
4. We diff against the empty file → parameter offset found

Create a reusable step-by-step guide so the user can produce calibration files for ANY console (DM7, TF, RIVAGE, DiGiCo, A&H) without needing per-console instructions from us. The guide should:
- Explain the method in plain language (user is an audio engineer, not a developer)
- List exactly what parameters to set and to what values
- Name the files consistently (e.g., `{console} calibration {param}.{ext}`)
- Cover: empty baseline, HPF, EQ all bands, dynamics full, fader/pan/mute, mix bus sends, mute groups, delay, HA/preamp

Save to `docs/guides/calibration-file-guide.md`.

---

## Current State Summary

### What's deployed
- **Railway:** Translation engine at `https://audiosolutions-production.up.railway.app` — Yamaha CL binary parser (CLF/CLE), DiGiCo SD writer, PDF report generator. 75 tests.
- **Vercel:** Web app at `https://audio-solutions-pied.vercel.app` — landing page, signup/login, upload flow, dashboard (pending R2 fix). 42 tests.
- **Supabase:** Auth + profiles + translations + anonymous_previews tables, RLS policies.
- **Cloudflare R2:** 3 buckets created (`showfier-sources`, `showfier-outputs`, `showfier-reports`).

### What's built but not yet deployed
- Binary CLF/CLE parser wired into translator + web upload accepts `.clf` — pushed to GitHub, auto-deploying.

### What's NOT built yet
- Plan 2b remaining: the R2 integration is deployed but untested end-to-end (blocked on R2 env var fix)
- Plan 3: Payments (Paddle) — not started
- DiGiCo parser for real `.show` files (only synthetic fixtures)
- Any non-CL Yamaha parser
- A&H parser

### Repository structure
```
AudioSolutions/
├── engine/          # Python FastAPI on Railway (75 tests)
│   ├── parsers/
│   │   ├── yamaha_cl.py          # Synthetic XML parser
│   │   ├── yamaha_cl_binary.py   # Real CLF/CLE parser ← NEW
│   │   └── digico_sd.py          # Synthetic XML parser
│   ├── writers/
│   ├── translator.py             # Auto-detects CLF vs ZIP format
│   └── tests/
├── web/             # Next.js on Vercel (42 tests)
├── samples/         # Real show files + calibration files
├── docs/
│   ├── research/yamaha-clf-format.md   # Complete binary format spec
│   ├── superpowers/specs/              # Design specs
│   └── superpowers/plans/              # Implementation plans
└── CLAUDE.md
```

### Key files for next session
- `docs/research/yamaha-clf-format.md` — the CLF binary format reference
- `engine/parsers/yamaha_cl_binary.py` — the parser to use as a template for new consoles
- `samples/` — all real show files and calibration files
