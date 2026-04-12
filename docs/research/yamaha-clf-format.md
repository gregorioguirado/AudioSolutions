# Yamaha CL/QL .CLF/.CLE Binary Format — Research Notes

**Status:** Core parameters mapped. Ready for parser implementation.
**Sources:** calibration files (empty, HPF+EQ+gate+comp, gate-only), Example 1/2 CL5, DOMCAS11.4
**Key finding:** CLE and CLF share identical binary data after their headers. Parse one = parse both.

---

## File Types

| Extension | Source | Format |
|---|---|---|
| `.CLF` | Console USB save | Binary, section table header starts at byte 0 |
| `.CLE` | CL Editor (desktop) | Binary, text header ~0x2A bytes longer, then same payload |

Post-MEMAPI data is byte-for-byte identical between CLF and CLE for the same show.

---

## File Structure Overview

### CLF Header (0x00 - 0x2F)
```
0x00: 01 00 00 00    — format version
0x04: 00 00 00 28    — header size (40 bytes)
0x08: 01 70 05 c0    — format identifier (CL5)
```

### Section Table (0x30+)
Each entry: `[4-byte offset] [2-byte section_id] [2-byte pad]`

Key sections:
- **0x0052** at offset 0x0158 — Channel setup (names, colors, patch)
- **0x0012** at offset 0x4D58 — Scene data (MEMAPI blocks with all mix parameters)

---

## Channel Setup (Global, Not Per-Scene)

### Channel Names
Two tables of 96 × 4 bytes = 8-character names.

| Table | Offset (CLF) | Content |
|---|---|---|
| First 4 chars | 0x22D5C | `"1 an"`, `"2 ba"`, ... |
| Last 4 chars | 0x22EDC | `"na"`, `"co"`, ... |

Full name = `Table1[i] + Table2[i]`, stripped of nulls.

### Channel Colors
96 × 1 byte at offset 0x2305C.
- `0x16` (22) = default input channel color
- `0x1D` (29) = return channel color
- Full palette mapping TBD (need file with varied colors)

### Input Patch
96 × 1 byte at offset ~0x22C4F. 1-indexed physical input numbers.

---

## Scene Data (MEMAPI Blocks)

Each scene marked by `MEMAPI` (6 bytes) + header:
```
+0x00: "MEMAPI" (6 bytes)
+0x06: 00 00 (padding)
+0x08: marker (2 bytes)
+0x0A: 00 00 (padding)
+0x0C: scene name (20 bytes, null-padded ASCII)
```

Scene block size: ~0xAE68 (44,648 bytes).

---

## Per-Channel Parameter Map (offsets relative to MEMAPI)

All confirmed by calibration file comparison (ch1 modified vs empty default).

### Boolean Enable Flags (1 byte per channel, 0=off, 1=on)

| Offset | Parameter |
|---|---|
| +0x0E84 | **Gate enable** |
| +0x1460 | **Compressor enable** |
| +0x1A30 | **HPF enable** |

### HPF Frequency (1 byte per channel)

**Offset:** +0x1A3C

**Encoding:** Logarithmic scale.
```
frequency_hz = 20 × 2^((index - 28) / 4.8)
```

| Index | Frequency |
|---|---|
| 28 | 20 Hz (default) |
| 33 | 40 Hz |
| 38 | 80 Hz |
| 40 | 113 Hz |
| 44 | 200 Hz |
| 50 | 500 Hz |
| 56 | 1140 Hz |

### Gate Threshold (2-byte stride table)

**Offset:** +0x1335

**Layout:** `[threshold_byte] [0xFE]` repeating, 2 bytes per channel.

**Encoding:** Reconstruct 16-bit big-endian as `0xFE00 | threshold_byte`, interpret as signed, divide by 10.
```
threshold_dB = (int16_be(0xFE, byte) - 65536) / 10
```

| Byte | 16-bit | Threshold |
|---|---|---|
| 0xFC | 0xFEFC = -260 | -26.0 dB (default) |
| 0xD4 | 0xFED4 = -300 | -30.0 dB |
| 0xB0 | 0xFEB0 = -336 | -33.6 dB |

### Compressor Threshold (2-byte stride table)

**Offset:** +0x1911

**Layout:** `[threshold_byte] [0xFF]` repeating, 2 bytes per channel.

**Encoding:** Same as gate but with 0xFF padding: `0xFF00 | threshold_byte`, signed, /10.
```
threshold_dB = (int16_be(0xFF, byte) - 65536) / 10
```

| Byte | 16-bit | Threshold |
|---|---|---|
| 0xB0 | 0xFFB0 = -80 | -8.0 dB (default) |
| 0x38 | 0xFF38 = -200 | -20.0 dB |

### EQ Band 1 (Low) Gain (1 byte per channel)

**Offset:** +0x1C64

**Encoding:** Linear, 6 units per dB, centered at 36 = 0 dB.
```
gain_dB = (value - 36) / 6
```

| Value | Gain |
|---|---|
| 0 | -6.0 dB |
| 36 | 0.0 dB (default/flat) |
| 72 | +6.0 dB |

### EQ Band 1 Unknown Parameter

**Offset:** +0x1CC5

Changed from 0x00 (default) to 0x3C (60) in calibration file where EQ low = +6 dB. Possibly EQ frequency offset, Q value, or band type. Needs further investigation with isolated EQ changes.

---

## Validated Against Real Show Files

Tested against "Example 2 CL5" (theater production, 44 scenes, ~64 channels):
- **HPF enable:** 61/72 channels enabled ✓ (theater: HPF on almost everything)
- **Compressor enable:** 60/72 channels enabled ✓ (ch13-72 = all actor/instrument channels)
- **Gate enable:** 2/72 channels enabled ✓ (gates rarely used on theater shows)
- **Gate thresholds:** non-default values found on channels with different gate settings ✓

---

## Parameters Still To Map

- EQ bands 2-4 (High-Mid, Low-Mid, High) — gain, frequency, Q, type
- EQ band 1 frequency and Q
- Gate attack, hold, decay, range
- Compressor ratio, attack, release, knee, makeup gain
- Channel fader level
- Channel mute/on state
- Pan position
- Mix bus send levels
- VCA/DCA assignments
- Channel color palette (full mapping)

---

## Next Steps

1. Build CLF parser with confirmed parameters (names, HPF, gate on/off + threshold, comp on/off + threshold, EQ band 1 gain)
2. Create additional calibration files to map remaining EQ parameters
3. Map the MBDF format (.dm7f, .tff, .RIVAGEPM) — shares `#YAMAHA MBDFProjectFile` header
