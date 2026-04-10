# Show File Universal Translator — Design Spec
**Date:** 2026-04-10
**Status:** Approved for implementation planning
**Project:** AudioSolutions

---

## 1. Product Overview

A cloud SaaS web application that allows live audio engineers to upload a mixing console show file from one brand and download a translated version for a different brand — without rebuilding from scratch.

**Tagline:** The Babel Fish for mixing consoles.

**Core value proposition:** A touring engineer arrives at a venue with the wrong console. Instead of spending 2–4 hours rebuilding their show file by hand, they upload it, wait 30 seconds, and download a ready-to-import file for the desk in front of them.

---

## 2. Market Analysis

### Target market
The global live events industry employs an estimated 30,000–80,000 professional audio engineers across touring, festivals, theater, and install markets. The touring and festival segment represents the highest pain and highest willingness to pay.

### Problem frequency
Console brand switching happens constantly:
- Festivals run mixed-brand console fleets across multiple stages
- Rental companies stock whatever is available, not what engineers prefer
- Show files represent months of rehearsal work that cannot be recreated in a pre-show window

### Competition
No direct competitor exists. This is a blue ocean in a niche market.
- Console manufacturers provide internal import/export tools only within their own ecosystems
- No cross-brand translation product exists commercially
- The status quo is manual recreation — hours of error-prone data entry

### Competitive moat
1. **First-mover** — owns the category name in a community-driven industry
2. **Word-of-mouth distribution** — live audio is referral-heavy; one respected engineer recommending the tool reaches hundreds
3. **Technical barrier** — reverse-engineering proprietary file formats takes significant time; 12–18 month head start minimum
4. **Data advantage** — each translation run surfaces edge cases; accuracy compounds over time

### Customer segments (priority order)
| Segment | Pain | Willingness to pay | Buyer type |
|---|---|---|---|
| Freelance touring FOH/monitor engineers | Very high | High | B2C (Pro) |
| Rental companies | High | High | B2B (Team) |
| Festival production companies | High | High | B2B (Team/Enterprise) |
| Theater sound designers | Medium | Medium | B2C/B2B |
| Venue/install engineers | Low | Low | Out of scope for MVP |

---

## 3. Business Model

### Pricing tiers

| Tier | Price | Limits | Notes |
|---|---|---|---|
| Free | $0 | 1 lifetime translation | Requires account creation; full output + report |
| Credits | $12 / $50 / $90 | 1 / 5 / 10 translations; no expiry | For one-off users |
| Pro monthly | $19/month | 30 translations/month | 1 concurrent session, 3 registered devices |
| Pro annual | $149/year | 30 translations/month | ~$12.40/mo effective |
| Team | $399/year | 10 seats, 30/seat/month | Shared history, team dashboard |
| Enterprise | Custom | Unlimited seats | SLA, API access, custom onboarding |

*Prices subject to change before launch.*

### Abuse prevention (Pro plan)
- One active session per account at a time — new login kicks existing session
- Maximum 3 registered devices per account — new device requires email verification
- 2 kick events in 30 days triggers mandatory re-verification
- Free trial: email verification + IP logging + browser fingerprinting (FingerprintJS) to deter multi-account abuse

### Conversion funnel
```
Community referral / Google search
        ↓
Account creation → 1 free lifetime translation (full output)
        ↓
"This saved me 3 hours" → credits or Pro subscription
        ↓
Regular use → annual Pro upgrade
        ↓
Employer / rental company → Team plan
```

### Payment infrastructure
- **MVP:** Paddle (Merchant of Record — handles all global tax compliance automatically; ~5% + $0.50/transaction)
- **Phase 2:** PIX via Pagar.me for Brazilian market (founder has existing community distribution channel in Brazil)

### Revenue projections (illustrative)
| Stage | Users | Estimated MRR |
|---|---|---|
| Early traction | 20 Pro annual, 5 Team | ~$500/mo |
| Growing | 100 Pro annual, 20 Team | ~$2,300/mo |
| Established | 300 Pro annual, 60 Team | ~$6,700/mo |

---

## 4. Technical Architecture

### Stack

| Layer | Tool | Purpose |
|---|---|---|
| Frontend | Next.js on Vercel | Web app — upload UI, dashboard, auth flows |
| Translation engine | Python FastAPI on Railway | File parsing, normalization, output generation |
| Database + auth | Supabase | User accounts, usage tracking, translation history |
| File storage | Cloudflare R2 | Uploaded source files + translated output files |
| Payments | Paddle | Subscriptions, credits, invoicing, global tax |
| Abuse prevention | FingerprintJS | Browser fingerprinting for free trial deduplication |

### System flow
```
1. Engineer visits site → creates account (email verified)
2. Selects source console (Yamaha CL5) and target console (DiGiCo SD12)
3. Uploads .cle file via browser
4. Next.js checks entitlement in Supabase (free trial / credits / subscription)
5. File forwarded to Python FastAPI engine on Railway
6. Engine: Parse → Normalize → Write → Report
7. Output file + translation report stored in Cloudflare R2
8. Engineer downloads both files
9. Usage count decremented in Supabase
```

### The translation engine (core IP)

The engine operates in three stages:

**Stage 1 — Parse**
Read the uploaded file and extract structured data.
- Yamaha CL/QL: `.cle` files are ZIP archives containing XML (e.g., `MixParameterData.xml`, `SceneData.xml`)
- DiGiCo SD/Quantum: `.show` files are XML-based
- Python libraries: `zipfile`, `lxml` / `xml.etree`

**Stage 2 — Normalize (the Babel layer)**
Convert parsed data into a console-agnostic universal internal format (Python dataclass / JSON schema). This is the core intellectual property.

Universal data model fields:
```
channels[]
  - id
  - name (string)
  - color (normalized hex)
  - input_patch (physical input number)
  - hpf_freq (Hz, float)
  - hpf_enabled (bool)
  - eq_bands[] (freq, gain, Q, type)
  - gate (threshold, attack, release, enabled)
  - compressor (threshold, ratio, attack, release, makeup_gain, enabled)
  - mix_bus_assignments[] (bus id, send level)
  - vca_assignments[] (vca id)
```

**Stage 3 — Write**
Generate a valid importable show file for the target console from the normalized model.

**Translation fidelity table**
| Parameter | Translates | Notes |
|---|---|---|
| Channel names | ✅ Always | Direct text copy |
| Channel colors | ✅ Usually | Nearest match from target palette |
| Input patch | ✅ Always | Physical input → channel mapping |
| HPF frequency | ✅ Always | Mathematically precise |
| EQ bands | ✅ Approximated | Band types differ per console |
| Gate/compressor | ✅ Approximated | Parameter ranges differ |
| Mix bus routing | ✅ Usually | Bus count differences handled |
| VCA assignments | ✅ Usually | |
| Brand-specific plugins | ❌ Never | Dropped, logged in report |
| Custom DSP (e.g. Yamaha Premium Rack) | ❌ Never | Dropped, logged in report |
| Scene/snapshot data | ❌ MVP | Phase 2 |

**Translation report (always generated)**
Every translation produces a report showing:
- ✅ Successfully translated parameters (with count)
- ⚠️ Approximated parameters (with explanation)
- ❌ Dropped parameters (with reason)

The report is the trust mechanism — engineers need to know exactly what happened before loading an unfamiliar file into a live console.

### File retention policy
| Tier | Source file | Output file | Report |
|---|---|---|---|
| Free / Credits | Deleted after 24h | Deleted after 24h | Deleted after 24h |
| Pro | 7 days | 7 days | Permanent |
| Team | 30 days | 30 days | Permanent |

---

## 5. MVP Scope

### In MVP
- Yamaha CL/QL → DiGiCo SD/Quantum (bidirectional)
- Web upload + download interface
- Account creation + email verification
- 1 free lifetime translation
- Credit purchases via Paddle
- Pro monthly + annual subscription via Paddle
- Translation report (PDF, downloadable alongside the output file)
- Basic usage dashboard (translations used this month)
- FingerprintJS abuse prevention on free tier

### Out of MVP (Phase 2+)
- Allen & Heath dLive, Midas PRO, SSL Live support
- Team plan + team dashboard
- Enterprise plan + API access
- PIX / Pagar.me (Brazilian market)
- Scene/snapshot translation
- Mobile-optimized UI
- Bulk translation (multiple files at once)

---

## 6. Infrastructure Costs

### Monthly running costs
| Service | Free tier | Paid tier | Trigger to upgrade |
|---|---|---|---|
| Vercel | Free (Hobby) | $20/mo (Pro) | Custom domain SSL, team features |
| Railway | $5 credit/mo | ~$10–20/mo | Sustained Python engine load |
| Supabase | Free (500MB, 50k MAU) | $25/mo (Pro) | >500MB DB or >50k users |
| Cloudflare R2 | 10GB free | $0.015/GB | >10GB stored files |
| Paddle | No monthly fee | ~5% + $0.50/tx | Per transaction |

### Cost by stage
| Stage | Monthly infra cost |
|---|---|
| Building / zero users | ~$0–5 |
| Early launch (0–50 users) | ~$25–40 |
| Growing (50–500 users) | ~$55–80 |
| Established (500+ users) | ~$100–200 |

### One-time costs
| Item | Estimated cost |
|---|---|
| Domain name | ~$15/year |
| Logo / basic branding | $0–200 |
| Legal (ToS, Privacy Policy) | $0–300 (Termly for MVP) |
| Console access for testing | Borrow from network |

### Critical pre-launch requirement
Real show files from real consoles are required for testing before launch:
- Yamaha CL/QL: real `.cle` files in various configurations
- DiGiCo SD/Quantum: real `.show` files
- Source: founder's audio engineering network (anonymized files from trusted contacts)

---

## 7. Key Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Console file formats change with firmware updates | Medium | Version-detect on parse; maintain a format changelog |
| Manufacturer legal challenge (reverse engineering) | Low-Medium | Output file is user's own data; translation is transformative. Consult a lawyer before launch. |
| Translation accuracy complaints at a live show | High (some cases) | Translation report sets expectations; clear "verify before show" warning in UI |
| Low search volume (niche market) | High | Community distribution is primary channel, not SEO |
| Credential sharing beyond built-in limits | Medium | Session enforcement + device limits + Team plan pricing |
