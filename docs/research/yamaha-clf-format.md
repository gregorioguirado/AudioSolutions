# Yamaha CL/QL .CLF/.CLE Binary Format — Complete Parameter Map

**Status:** Ready for parser implementation
**Sources:** 9 calibration/sample files (empty, EQ-all-bands, dynamics-full, fader-pan-mute, gate-only, full-calibration, Example 1/2, DOMCAS11.4)
**Key finding:** CLE and CLF share identical binary data after their headers. Parse one = parse both.

---

## File Types

| Extension | Source | Format |
|---|---|---|
| `.CLF` | Console USB save | Binary, section table header starts at byte 0 |
| `.CLE` | CL Editor (desktop) | Binary, text header ~0x2A bytes longer, then same payload |

Post-MEMAPI data is byte-for-byte identical between CLF and CLE for the same show.

---

## File Structure

### Header
```
0x00: 01 00 00 00    — format version
0x04: 00 00 00 28    — header size (40 bytes)
0x08: 01 70 05 c0    — format identifier (CL5)
0x30+: Section table — entries: [4-byte offset] [2-byte section_id] [2-byte pad]
```

### Key Sections
- **0x0052** — Channel setup (names, colors, patch) — global, not per-scene
- **0x0012** — Scene data (MEMAPI blocks with all mix parameters)

---

## Channel Setup (Global, Not Per-Scene)

### Channel Names
Two consecutive tables of 96 entries × 4 bytes, combining into 8-character names.

| Table | Offset (CLF) | Content |
|---|---|---|
| First 4 chars | 0x22D5C | Short name part 1 |
| Last 4 chars | 0x22EDC | Short name part 2 |

Full name = `Table1[i] + Table2[i]`, stripped of nulls.
96 entries: ch1-72 inputs, ch73-88 returns/ST, ch89-96 additional.

### Channel Colors
96 × 1 byte at offset **0x2305C**.
- `0x16` (22) = default input channel color
- `0x1D` (29) = return channel color
- Full palette mapping TBD

### Input Patch
96 × 1 byte at offset **~0x22C4F**. 1-indexed physical input numbers.

---

## Scene Data

Each scene marked by `MEMAPI` (6 bytes):
```
+0x00: "MEMAPI" (6 bytes)
+0x06: 00 00 (padding)
+0x08: marker (2 bytes, e.g., 0x189A)
+0x0A: 00 00 (padding)
+0x0C: scene name (20 bytes, null-padded ASCII)
```

Scene block size: ~0xAE68 (44,648 bytes). All offsets below are relative to MEMAPI.

---

## Per-Channel Parameter Map

### Enable Flags (1 byte per channel, 0=off, 1=on)

| Offset | Parameter | Confirmed by |
|---|---|---|
| +0x0E84 | Gate enable | gate-only calibration |
| +0x1460 | Compressor enable | full calibration |
| +0x1A30 | HPF enable | full calibration |

### HPF

| Offset | Parameter | Encoding |
|---|---|---|
| +0x1A3C | Frequency | 1B/ch, logarithmic: `freq_hz = 20 × 2^((val - 28) / 4.8)` |

Verified: index 28 = 20 Hz, index 44 = 200 Hz.

### Gate

| Offset | Parameter | Encoding |
|---|---|---|
| +0x1094 | Attack | 1B/ch, `attack_ms = value` (default 0 = 0ms) |
| +0x10F4 | Hold | 1B/ch, logarithmic: `hold_ms = 2.33 × 2^((val - 200) / 3.60)` |
| +0x1154 | Decay | 1B/ch, logarithmic (inverse — higher value = shorter time) |
| +0x11B4 | Range | 1B/ch (default 44 = -56dB, val 35 = -40dB) |
| +0x1335 | Threshold | 2B stride `[val][0xFE]`, reconstruct as `0xFE00 | val`, signed16 / 10 = dB |

Default gate: threshold -26dB, range -56dB, decay 304ms, attack 0ms, hold 2.33ms.

### Compressor

| Offset | Parameter | Encoding |
|---|---|---|
| +0x1670 | Attack | 1B/ch, `attack_ms = value` (default 30 = 30ms) |
| +0x1790 | Release | 1B/ch, logarithmic: `release_ms = 46.5 × 2^(val / 16.1)` |
| +0x17F0 | Ratio | 1B/ch, approximately `ratio = 2^(val / 4.4)` (default 6 = 2.5:1) |
| +0x1850 | Makeup gain | 1B/ch, `gain_dB = value / 10` (default 0 = 0dB) |
| +0x18B0 | Knee | 1B/ch, direct value (default 2) |
| +0x1911 | Threshold | 2B stride `[val][0xFF]`, reconstruct as `0xFF00 | val`, signed16 / 10 = dB |

Default compressor: threshold -8dB, ratio 2.5:1, attack 30ms, release 229ms, knee 2, makeup 0dB.

### EQ (4 Bands)

4 bands, each stored as 4 consecutive tables of 96 bytes (384 bytes per band, 1536 total).

| Band | Base offset | Default freq | Freq index |
|---|---|---|---|
| Band 1 (Low) | +0x1C00 | 125 Hz | 36 |
| Band 2 (Low-Mid) | +0x1D80 | 1000 Hz | 72 |
| Band 3 (High-Mid) | +0x1F00 | 4000 Hz | 96 |
| Band 4 (High) | +0x2080 | 10000 Hz | 112 |

Within each band (tables at base+0, base+96, base+192, base+288):
- **Table 0 (+0):** Band type/enable flags
- **Table 1 (+96):** Frequency — 1B/ch, semitone scale: `freq_hz = 20 × 2^((val - 4) / 12)`
- **Table 2 (+192):** Gain — 2B signed big-endian per channel, `gain_dB = signed_value / 10`
- **Table 3 (+288):** Reserved/unused

EQ frequency verified across all 4 bands (125→200, 1000→800, 4000→3000, 10000→8000 Hz), all within 2.4% accuracy. 12 steps per octave = semitone scale.

**Q values** stored separately:
- Band 1 Q: +0x95F8 (1B/ch, default 30 = Q 4.0, val 39 = Q 2.0)
- Band 2 Q: +0x9658 (1B/ch, default 30 = Q 0.7, val 35 = Q 1.6)
- Band 3/4 Q: TBD (not yet located — different band has different Q defaults at same index)

### Fader / Pan / Mute

| Offset | Parameter | Encoding |
|---|---|---|
| +0x09C6 | Pan | 1B/ch, signed: -63 = hard L, 0 = center, +63 = hard R |
| +0x0A26 | Fader level | 2B/ch big-endian, 0 = -inf, 959 (0x03BF) = 0dB |
| +0x53FE | Channel OFF flag | 1B/ch (0=on, 1=off) |

### Delay

| Offset | Parameter | Encoding |
|---|---|---|
| +0x0AE6 | Delay enable | 1B/ch, 0=off, 1=on |
| +0x0B02 | Delay time | 2B/ch big-endian, `time_ms = value / 100` |

Verified: 996 / 100 = 9.96 ms.

### HA / D.GAIN / 48V / Phase / Direct Out

| Offset | Parameter | Encoding |
|---|---|---|
| +0x0822 | Enable flag | 1B/ch (0=off, 1=on) — related to direct out or HA state |
| +0x082E | Bitfield | 1B/ch, possibly `bit0 = 48V, bit1 = phase` (val=3 = both ON) |
| +0x094E | Direct out enable | 1B/ch (0=off, 1=on) |
| +0x0C8D | D.GAIN | 1B/ch, `gain_dB = value / 10` (val 100 = +10.0 dB) |
| +0x7B14 | HA analog gain | 1B/ch, `gain_dB = value - 6` (val 26 = +20 dB, default 0 = -6 dB) |
| +0x7D34 | Enable flag | 1B/ch (TBD — related to direct out post/pre) |
| +0x7D74 | HA gain (duplicate?) | 1B/ch, same value as +0x7B14 |

### DCA Assignments

| Offset | Parameter | Encoding |
|---|---|---|
| +0x2720 | DCA 1-8 assignments | 12-byte stride per DCA, 1B per channel within each DCA block |

DCA 1 at +0x2720, DCA 2 at +0x272C, DCA 3 at +0x2738, etc. (stride = 12 bytes).
Value 0 = not assigned, 1 = assigned.

### Mute Groups

| Offset | Parameter | Encoding |
|---|---|---|
| +0x26C0 | Mute Group 1-8 assignments | 12-byte stride per group, 1B per channel |

MG1 at +0x26C0, MG2 at +0x26CC, MG3 at +0x26D8, etc. (stride = 12 bytes).
Value 0 = not assigned, 1 = assigned.

### Mix Bus Sends (24 mixes)

Each mix bus = 216 bytes (0xD8):
- **Bytes 0-11:** Other flags/data
- **Bytes 12-23:** PRE/POST bitfield (12 bytes = 96 bits, 1 per channel; bit=1=PRE, bit=0=POST)
- **Bytes 24-215:** Send levels (96 × 2 bytes big-endian, Yamaha level curve: 0=-inf, 823=0dB)

| | |
|---|---|
| Mix 1 sends start | scene +0x28F4 |
| Mix 1 PRE/POST | scene +0x28E8 (12 bytes) |
| Stride per mix | 216 bytes |
| Total mixes | 24 (Mix 1-24) |
| Total block size | 5184 bytes |

Ch1 = bit 0 of the first PRE/POST byte. Ch1 send level = first 2 bytes of the send table.

---

## Encoding Reference

### Frequency scales

| Context | Formula | Verified range |
|---|---|---|
| HPF frequency | `20 × 2^((val - 28) / 4.8)` | 20 Hz – 2000+ Hz |
| EQ frequency | `20 × 2^((val - 4) / 12)` | 20 Hz – 20 kHz (semitone scale) |

### Gain/threshold scales

| Context | Formula |
|---|---|
| Gate/Comp threshold | Reconstruct 16-bit signed, divide by 10 = dB |
| EQ band gain | 2B signed big-endian, divide by 10 = dB |
| Comp makeup gain | 1B unsigned, divide by 10 = dB |

### Time scales

| Context | Formula |
|---|---|
| Gate/Comp attack | Direct value in ms |
| Gate hold | `2.33 × 2^((val - 200) / 3.60)` ms |
| Comp release | `46.5 × 2^(val / 16.1)` ms |
| Channel delay | 2B BE, `time_ms = value / 100` |

### Other scales

| Context | Formula |
|---|---|
| HA analog gain | `gain_dB = value - 6` (default 0 = -6 dB) |
| D.GAIN | `gain_dB = value / 10` |
| Comp ratio | Approximately `ratio = 2^(val / 4.4)` |
| Pan | Signed byte: -63 = hard L, 0 = center, +63 = hard R |

---

## Validation

Tested against real show files (Example 1/2 = Brazilian theater production, 44 scenes, 64 channels):
- HPF enable: 61/72 channels ✓
- Compressor enable: 60/72 channels (ch13-72 = vocals/instruments) ✓
- Gate enable: 2/72 channels ✓
- Channel names: "1 anna", "3 breno", "10 grego", "41 viola", "43 banjo" ✓
- Scene names: "Sesc pinlheiros", "master FLAT", "Manifesto", "baile cobras" ✓

---

## Remaining Gaps

### Minor (won't block parser)
- EQ Q values for bands 3 and 4 (bands 1-2 mapped at +0x95F8 and +0x9658)
- EQ band type/enable flags (table 0 of each band)
- Channel color full palette mapping (index→color name)
- Gate decay exact encoding formula (log scale, values known)
- Gate range exact encoding formula (values known)
- +0x7B14 vs +0x7D74: determine which is HA gain vs duplicate/other param
- +0x082E bitfield: confirm bit assignments for 48V and phase
- Recall safe and mute safe flags (not yet investigated)

### Not investigated
- Output patching (Dante/OMNI routing beyond input patch)
- Insert assignments
- Stereo/Mono channel linking
- Scene recall safe filters
