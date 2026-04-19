# Council-Driven Shifts to the Showfier Plan

**Date:** 2026-04-18
**Source council session:** `docs/council/council-report-2026-04-18-1628.html` · `docs/council/council-transcript-2026-04-18-1628.md`
**Affected doc:** `docs/showfier-project-overview-and-market-analysis.md`

This is a **delta document** — not a replacement plan. It lists the changes that should be applied to the existing project-overview-and-market-analysis doc based on the LLM Council verdict. Each change is tagged with the category of shift (KILL / ADD / REORDER / POSITIONING / REJECTED) and the council advisor(s) who drove it.

---

## KILL — explicitly removed from roadmap

These items were in `§9 Product Roadmap` of the existing plan. They are deferred indefinitely until the earlier phases land paying customers.

| Removed item | Was in | Rationale |
|---|---|---|
| Mobile app · offline desktop · CLI · webhooks · marketplace | §9 Phase 5 | Solo founder, pre-revenue. Zero of these ship value before $5K MRR. |
| Scene builder · template library · version control · input list manager | §9 Phase 3 | Scope creep. None of these are on the critical path to a paying customer. |
| API v1 · Team plans | §9 Phase 3 | Enterprise sales muscle doesn't exist yet. Ship individual-engineer product first. |
| Technical rider parser (OCR/AI) · patch sheet manager · X32/Wing · rental-company API integrations | §9 Phase 4 | Distraction from Big Three (Yamaha + DiGiCo + A&H). |
| NAMM · Prolight+Sound · PLASA · AES trade-show presence | §8 GTM Tier 2 | Costs time and money you don't have yet. Brazilian WhatsApp groups are free and warmer. |

**Driving advisor:** The Executor, unanimously supported in peer review.

---

## ADD — new items the original plan did not contain

| New item | Owner | Rationale |
|---|---|---|
| **Verification harness** — automated round-trip CI that diffs every translation against source; re-runs on every parser change | New Phase 2 cornerstone | Firmware-treadmill defense (Contrarian) + trust artifact (peer review). Turns "validate DiGiCo" from a one-time manual check into a continuous correctness guarantee. |
| **"Verify on console before doors" UX step** — explicit acknowledgment inside the translation download flow, not buried in ToS | Translation flow | Liability / show-day failure mode. Peer reviewers 4/5 independently flagged this as the single biggest blind spot no advisor raised. |
| **Friday discovery sidecar** — 1 call/week with rental companies or touring engineers. Discovery only, not a build track | Ongoing from Phase 5 onward | Keeps the First Principles reframe ("portable show, rental-company buyer") alive as a future option. Generates pivot data without splitting the shipping budget. |
| **Immediate pricing table fix** — the current 5-credit pack costs more per credit than buying singles | §6 · pre-Paddle | Unforced trust-destroying bug the Outsider caught. |
| **Dedicated "legal cover before payments" phase** — E&O quote paid + ToS with liability cap + show-day disclaimer must ship before Paddle charges a single card | New Phase 1 gate | Peer reviewers flagged liability as the product-ending risk no advisor named. The existing doc's §14 has the disclaimer copy drafted — the shift is on *when* it ships, not whether. |

**Driving advisors:** Peer review (liability), Outsider (pricing), First Principles (rental-company discovery).

---

## REORDER — same items, different sequence

| Item | Was | Now |
|---|---|---|
| E&O insurance + ToS with liability cap | §14, deferred | Ships **before Paddle**, not after. Hard gate. |
| DiGiCo real-file validation | Implicit across roadmap | Explicit **Phase 1 gate**. No Paddle integration until output loads cleanly in DiGiCo Offline Software. Everything downstream is conditional on this binary yes/no. |
| Allen & Heath dLive parser | §10 priority #1 (Month 3–5) | Waits until CL↔DiGiCo is validated on real traffic AND Yamaha MBDF family ships. |
| Yamaha QL validation | §10 priority #4 (Month 6–8) | Moved up to Month 2 — shares the CL binary format, near-zero effort to add. |
| Rental-company partnerships | §8 Tier 1 GTM channel | Repositioned as **discovery-first, partnership-later**. Friday sidecar calls open the door; partnership conversations only after revenue is validated. |

**Driving advisors:** Executor (DiGiCo gate), peer review (legal cover), Expansionist + First Principles (rental companies as buyer, not channel).

---

## POSITIONING SHIFT

### Pricing (replaces §6 Pricing Tiers table)

The existing 8-tier table (Free / $5 single / $45 pack of 5 / $80 pack of 10 / Pro $19/mo / Pro $149/yr / Team $599/yr / Enterprise) is cut to **three tiers**:

| Tier | Price | Limit |
|---|---|---|
| **Free** | $0 | 1 lifetime translation |
| **Pro** | $19/mo (or $149/yr) | Unlimited translations |
| **Team** | Contact for pricing | Multi-seat, custom |

Rationale: the Outsider caught that the 5-pack was priced higher per credit than singles (unforced trust bug). Five tiers of credits + subscription + team + enterprise creates decision paralysis for a solo engineer who just wants to translate one file before doors. Three tiers cover the three real buying modes: "try it," "use it regularly," "buy it for my company."

### Landing-page copy (edits §10 Hero / existing landing)

The brutalist aesthetic stays (rebrand is out of scope) — but the hero copy and key phrases change per the Outsider's critique:

- Explain `.CLE` in plain language on first view (not just "DROP .CLE HERE").
- Rewrite the tagline from the abstract "Stop rebuilding your shows" toward something legible to someone outside live audio. Candidate: *"Switch console brands in 30 seconds, not 8 hours."*
- Drop the "1 lifetime conversion" framing — it reads as a tripwire, not a trial. Use "1 free translation" without "lifetime."

### TAM honesty (edits §4 Market Analysis)

The 20K–40K touring-engineers claim stays as aspirational/marketing framing but **internal planning uses 2K–4K as the realistic paying market** (Contrarian correction). Revenue targets and runway assumptions rebase on the smaller number. This prevents the founder from fooling themselves about conversion math.

---

## REJECTED — proposed by advisors but NOT adopted

| Proposal | Advisor | Why not adopted |
|---|---|---|
| $30M ARR / $200M Audiotonix acquisition / "MIDI moment for consoles" / Universal Schema play | Expansionist | Rejected as near-term driver. Peer review unanimously flagged this as the biggest blind spot — assumes distribution, schema legitimacy, and trust that a pre-revenue MVP has not earned. Revisit only if/when >100 paying customers AND a rental-company pilot contract signs. |
| Full product pivot to "portable show, not file translator" (console-agnostic cloud show document as the core product) | First Principles | Not adopted as a pivot. Kept alive as a *future option* via the Friday discovery sidecar. Premature to reframe the product before 50 engineers have paid $19. |
| "This is a side-income tool, not a business" verdict | Contrarian | Acknowledged as a valid outcome, not accepted as destiny. Revenue milestones at Month 3 (20–25 paying) and Month 6 (first rental pilot conversation) are the falsifiable tests. If those miss, the Contrarian's framing becomes operative and the product becomes side-income while touring funds life. |

---

## DOC-LEVEL EDIT LIST

The following sections of `docs/showfier-project-overview-and-market-analysis.md` need direct edits to reflect the shifts above:

- **§6 Business Model & Pricing** — rewrite the pricing tier table to 3 tiers.
- **§8 Go-to-Market Strategy** — demote trade shows from Tier 2 to "deferred"; promote Friday sidecar + forum seeding + Brazilian WhatsApp to Tier 1.
- **§9 Product Roadmap** — strike every item listed in the KILL section above; insert **Verification Harness** as a Phase 2 cornerstone; move Yamaha QL ahead of Allen & Heath dLive in sequence.
- **§10 Console Support Priority** — reorder: CL/QL (done) → DiGiCo real-file (current gap) → Yamaha MBDF family (DM7/TF/RIVAGE batch-win) → A&H dLive → everything else deferred.
- **§12 Risk Matrix** — elevate "DiGiCo writer not validated on real console" to near-term risk #1; add "Liability / show-day failure" as a new top-5 risk with E&O + ToS + verify-before-doors UX as the mitigation stack.
- **§14 Policies & Compliance** — reframe: E&O premium paid and ToS with liability cap ship **before** Paddle accepts the first charge.
- **§16 Strategic Recommendations** — reorder "The Five Things That Matter Most" to: (1) Validate DiGiCo writer on a real console/Offline Software; (2) Ship legal cover (E&O + ToS) before Paddle; (3) Build verification harness; (4) MBDF batch-win (DM7 + TF + RIVAGE); (5) A&H dLive only after DiGiCo proven on real traffic.

---

## The One Thing To Do First

Unchanged from the council report: **validate the synthetic DiGiCo XML output in DiGiCo Offline Software before anything else.** Loads cleanly → the rest of the shifts apply and execution starts. Doesn't load → there is no product yet, and every shift above waits until it does.
