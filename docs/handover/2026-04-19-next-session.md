# Handover — 2026-04-19

## Where we are

Working on `main` (nothing in progress, everything pushed, 117 engine tests green, 80 web tests green).

The big thing that just happened: **Yamaha DM7 MBDF parser is done and live** (`engine/parsers/yamaha_dm7.py`). DM7 → CL/QL is now a working translation path. The format was reverse-engineered from Yamaha's own descriptor XMLs in `C:\Program Files\YAMAHA\DM7\Descriptor\` plus two calibration files the user saved.

---

## DM7 parser — what's done and what's missing

**Done (committed, tested — 128 tests green):**
- 120-channel name extraction (64-byte null-padded strings)
- HPF: frequency (÷10 for Hz) + On/Off flag at offset 134
- Color → ChannelColor enum
- DCA assignments (24-bit bitmask)
- Phase bit
- **EQ bands** — fully implemented. All offsets analytically derived from `mms_Mixing.xml` and verified against `dm7_empty.dm7f` defaults + `Bertoleza Sesi Campinas.dm7f` real values. 4 bands per channel; Band 1 = Low Shelf, Band 4 = High Shelf (controlled by LowShelving.On / HighShelving.On bits within the active PEQ bank). Freq ÷10 = Hz, Gain ÷100 = dB, Q ÷1000.
- **Dynamics** — type detection (GATE, Classic Comp, PM Comp, etc.) and threshold parsing. Threshold = Param[0] ÷ 100 dB (verified empirically). Gate and Compressor `.enabled` flags are correct.

**Still needed:**
- **Dynamics time constants** — attack/hold/release for Gate and attack/release for Compressor. Param scaling is type-dependent and unverified. Requires calibration file with known time values set. Currently set to 0.0 with a note in `dropped_parameters`.
- **Compressor ratio** — same issue; Param[1] scaling unclear (could be ÷10 for direct ratio). Needs calibration.
- **Mix bus sends** — ToMix collection (offset TBD).
- **DM7 writer** — To translate CL → DM7. Requires recompressing the inner blob; the 32-char hex strings in MBDF headers may or may not be content hashes (needs testing).

**To calibrate dynamics time constants/ratio (optional but good to have):**
Open DM7 Editor, load `samples/dm7_empty.dm7f`, set channel 1 with:
- Gate: Threshold -30dB, Attack 5ms, Hold 100ms, Release 200ms, ON
- Compressor: Classic Comp, Threshold -20dB, Ratio 4:1, Attack 10ms, Release 100ms, ON

Save as `samples/dm7_dyn_calibration.dm7f`. Then run `python tools/dm7_offset_probe.py samples/dm7_dyn_calibration.dm7f 1` to see the raw Param values and back-calculate scaling.

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
| Yamaha DM7 (.dm7f) | ✅ partial | ❌ | Names + HPF + EQ + dyn threshold done; dyn time constants/ratio TODO |
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
