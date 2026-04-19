# Handover — 2026-04-19

## Where we are

Working on `main` (nothing in progress, everything pushed, 117 engine tests green, 80 web tests green).

The big thing that just happened: **Yamaha DM7 MBDF parser is done and live** (`engine/parsers/yamaha_dm7.py`). DM7 → CL/QL is now a working translation path. The format was reverse-engineered from Yamaha's own descriptor XMLs in `C:\Program Files\YAMAHA\DM7\Descriptor\` plus two calibration files the user saved.

---

## DM7 parser — what's done and what's missing

**Done (committed, tested):**
- 120-channel name extraction (64-byte null-padded strings)
- HPF: frequency (÷10 for Hz, range 20–2000 Hz) + On/Off flag at offset 134
- Color → ChannelColor enum
- DCA assignments (24-bit bitmask)
- Phase bit

**Still needed (TODOs in the parser):**
- **EQ bands** — PEQ collection at record offset ~186. Needs calibration files with known EQ values set in DM7 Editor. The descriptor XML at `mms_Mixing.xml` shows the structure but we need empirical verification.
- **Gate & compressor** — Dynamics collection at ~481. Same — calibration files needed.
- **Mix bus sends** — ToMix collection (offset TBD).
- **DM7 writer** — To translate CL → DM7. The tricky part is recompressing the inner blob + potentially updating the file checksum (the 32-char hex strings in the MBDF headers may or may not be content hashes — needs testing).

**To generate DM7 EQ/dynamics calibration files:**
Open DM7 Editor (`C:\Program Files\YAMAHA\DM7\dm7_editor.exe`), load `samples/dm7_empty.dm7f`, set channel 1 with:
- HPF ON, 200 Hz
- EQ band 1: Bell, 1kHz, +6dB, Q=1.0
- Gate: Threshold -30dB, on
- Compressor: 4:1 ratio, -20dB threshold, on

Save as `samples/dm7_eq_dynamics_calibration.dm7f`. Then I can map those offsets.

---

## Other sample files already in `samples/`

- `Bertoleza Sesi Campinas.dm7f` — real DM7 show (used for parser verification)
- `RIVAGE EMI 21.3.RIVAGEPM` — RIVAGE PM file (same MBDF format, untouched)
- `DOM CASMURRO 2.tff` — TF series file (same MBDF format, untouched)

Both RIVAGE and TF share the MBDF container. Their descriptor XMLs would be in the respective editor install directories. They'd be fast to add once DM7 is complete.

---

## Console support status

| Console | Parse | Write | Notes |
|---------|-------|-------|-------|
| Yamaha CL/QL (XML .cle) | ✅ | ✅ | Full |
| Yamaha CL/QL (binary .clf/.cle) | ✅ | ✅ | Full |
| DiGiCo SD/Quantum | ✅ | ✅ | XML-based |
| Yamaha DM7 (.dm7f) | ✅ partial | ❌ | Names + HPF done; EQ/dynamics TODO |
| Yamaha TF (.tff) | ❌ | ❌ | MBDF, sample file exists |
| RIVAGE PM (.RIVAGEPM) | ❌ | ❌ | MBDF, sample file exists |

---

## Infrastructure state

- Dev server: `cd web && npm run dev` (port 3000)
- Engine tests: `cd engine && python -m pytest`
- Web tests: `cd web && npm test`
- Push: already done, remote is up to date
- No open branches

## Open decisions (not urgent)

- **Paddle + PIX**: Payment integration on hold. If implemented, PIX is mandatory co-launch.
- **DiGiCo Phase 0**: Still needs manual validation in DiGiCo Offline — blocks the confidence gate.
- **QL Editor update**: Still on v5.1.1. User can manually run `C:\Users\grego\AppData\Local\Temp\ql_edt581_win\ql_edt581_win\setup.exe` to update to 5.8.1 (the silent install failed; needs a manual click-through).
- **E&O insurance**: Deferred — no budget currently.
