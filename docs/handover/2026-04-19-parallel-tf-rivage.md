# Parallel Parser Sprint — Yamaha TF + RIVAGE PM

## Context

This doc briefs two parallel agents working on new parsers.  
The project is **Showfier** — a cloud SaaS that translates mixing console show files between brands so live audio engineers don't have to rebuild from scratch on unfamiliar gear.

We are building a Show File Universal Translator. The engine lives in `engine/`. Parsers go in `engine/parsers/`. Tests go in `engine/tests/`. Sample files are in `samples/` (project root).

**Current state:** 128 engine tests green. Three parsers already working: Yamaha CL/QL (XML + binary), DiGiCo SD/Quantum, Yamaha DM7 (just finished — EQ + Gate + Classic Comp fully calibrated).

---

## Shared knowledge: the MBDF container

Both TF and RIVAGE use the same **#YAMAHA MBDF** outer container as the DM7. The decompression + data-section-finding code from `engine/parsers/yamaha_dm7.py` works identically for all three. Both sample files decompress correctly.

```python
# Same for TF, RIVAGE, and DM7:
inner = _decompress_inner(data)     # finds zlib block, decompresses
data_start = _find_data_start(inner) # MMSXLIT → reads schema_size → skips to binary data
```

Copy these two helpers wholesale. The schema embedded in the MMSXLIT header is in binary format (COL0 records) for TF and RIVAGE — you don't need to parse the schema at all. The field offsets are derived empirically below.

**Python environment:** `"/c/Users/grego/AppData/Local/Microsoft/WindowsApps/python.exe"`  
**Run tests:** `cd engine && [python] -m pytest tests/ -q`

---

## Universal model

Parsers must return a `ShowFile` from `engine/models/universal.py`. The important fields per channel:

```python
Channel(
    id=1,
    name="KICK",
    color=ChannelColor.BLUE,       # ChannelColor enum
    input_patch=None,
    hpf_frequency=80.0,            # Hz
    hpf_enabled=True,
    eq_bands=[EQBand(...)],        # list of 4 EQBand objects
    gate=Gate(...),                # or None
    compressor=Compressor(...),    # or None
    mix_bus_assignments=[],
    vca_assignments=[],
    muted=False,
)
```

See `engine/parsers/yamaha_dm7.py` for a complete working reference — use it as a template.

---

## Agent A: Yamaha TF Series (.tff)

### Sample file
`samples/DOM CASMURRO 2.tff` — real TF5 show, "DOM CASMURRO 2" production

### What's known (empirically verified)

```python
RECORD_SIZE = 515     # bytes per InputChannel record
                      # (channel boundaries confirmed by recurring Category string gap)
```

The Mixing data section is **38324 bytes** (from `data_start` to the next MMSXLIT).  
38324 / 515 = ~74 channels + ~214 bytes trailing (buses/metadata — ignore for now).  
Parse up to `mixing_data_end` without overrunning.

**Label layout (verified from DOM CASMURRO 2.tff, ch1):**

| Offset | Field | Size | Notes |
|--------|-------|------|-------|
| +0 | Category | 16 bytes | `"Vocal"`, `"Perc"`, etc. — instrument type. Not in universal model; can be ignored or used for `input_patch` hinting. |
| +16 | Name | 64 bytes | User-set channel name. **This is the primary name to use.** |
| +80 | Color | 8 bytes | `"Blue"`, `"Red"`, etc. — same strings as DM7. Reuse `_map_color()`. |
| +88 | Icon | 12 bytes | `"DynamicMic"`, `"Kick"`, etc. — ignore or use as fallback name hint. |

**Verified ch1:** Category=`"Vocal"`, Name=`"KICK"`, Color=`"Blue"`, Icon=`"DynamicMic"`  
**Verified ch2:** Category=`"Vocal"`, Name=`"FX"` (FX return channel in this show)

**TF Editor NOT installed** on this machine. No descriptor XML available for field offsets beyond Label.

### What needs calibration

HPF frequency, HPF On/Off, EQ band offsets, and dynamics offsets are **unknown** and must be found empirically.

**Recommended approach:**

1. Write and commit a skeleton parser that extracts Name, Color from the verified offsets.
2. Write a probe script `tools/tf_offset_probe.py` (model it on `tools/dm7_offset_probe.py`) to dump raw bytes at candidate HPF/EQ offsets.
3. To find HPF: search for patterns like `01 XX XX 00 00` (On=1 then uint32 frequency) near offsets 100-300 in record 0 (KICK typically has HPF ~60-100 Hz → raw value = 600-1000 as uint32 LE). In the `DOM CASMURRO 2.tff` raw hex, there are frequency-like values starting around offset 140:
   ```
   144: 01 e2 04 00 00 (01=On?, 0x4e2=1250÷10=125Hz)
   ```
   This is a strong HPF candidate. Verify against a second channel.
4. If you can't nail offsets empirically, request a calibration file: have the user open TF Editor, load a blank show, set ch1 HPF ON 200Hz and one EQ band, save as `samples/tf_hpf_eq_calibration.tff`.

**Important note on TF vs DM7 differences:**
- TF Label starts at +0 with Category; DM7 starts at +0 with GainGang/DelayGang bits then Signal. Different start structure.
- TF has 4 HPF banks (like DM7) or possibly just 1 — unknown.
- TF PEQ likely has a similar structure to DM7 (4 bands, Bank system) based on the schema, but the byte offsets will differ.

### Deliverable

A working `engine/parsers/yamaha_tf.py` that:
1. Detects `.tff` files (same MBDF magic as DM7)
2. Extracts Name, Color per channel (already have offsets)
3. Extracts HPF (even if calibration-pending, document the offset and mark `TODO`)
4. Skips EQ/dynamics until calibration files are available
5. At least 5 tests in `engine/tests/test_yamaha_tf_parser.py` covering file detection, channel names, and color

Source console string: `"yamaha_tf"`

---

## Agent B: Yamaha RIVAGE PM (.RIVAGEPM)

### Sample file
`samples/RIVAGE EMI 21.3.RIVAGEPM` — real RIVAGE PM10 show, EMI Records production

### What's known (empirically verified)

```python
RECORD_SIZE = 1890    # bytes per InputChannel record
                      # (consistent 1890-byte gap between "STEREO" and "Blue" across 144 occurrences)
N_CHANNELS = 144      # 144 input channels confirmed by 144 occurrences of "STEREO" signal type
```

The Mixing data section is **540732 bytes**. The first 144 × 1890 = 272160 bytes are InputChannels. The remainder (268572 bytes) contains buses, FX, matrices — stop at channel 144 and don't overrun.

**Label layout (verified from RIVAGE EMI 21.3.RIVAGEPM, channels 1–20):**

| Offset | Field | Size | Notes |
|--------|-------|------|-------|
| +0 | GainGang+DelayGang | 1 byte | Packed bits — same as DM7 |
| +1 | Signal.Relation | 1 byte | Usually 0 |
| +2 | Signal.StereoInputType | 8 bytes | `"STEREO"` for all 144 input channels |
| +10 | Label.Name | 64 bytes | **Primary channel name** |
| +74 | Label.Color | 8 bytes | `"Blue"`, etc. |
| +82 | Label.Icon | 12 bytes | `"Kick"`, `"Snare"`, `"DynamicMic"`, etc. |

**Verified ch1–20:** sig=`"STEREO"`, name=`"ch1"`–`"ch20"` (default names in this show), color=`"Blue"`, icon=instrument type.

Note: this RIVAGE show uses default names ("ch1"–"ch20") with Icon as the channel identifier. That's a valid RIVAGE workflow — many operators name channels by icon rather than text. Extract whatever is in the Name field; if blank/default, it's fine.

**RIVAGE Editor NOT installed** on this machine. No descriptor XML available.

**Critical: RIVAGE label shares the DM7 layout** (GainGang prefix + Signal + Name@10/Color@74/Icon@82). This suggests RIVAGE and DM7 may share HPF offsets too. DM7 HPF offsets for reference:
```python
HPF_ON_OFFSET    = 134   # bit
HPF_FREQ_OFFSET  = 135   # uint32_t, ÷10 → Hz
HPF_SLOPE_OFFSET = 139   # uint8_t
```

Try these offsets first. The RIVAGE record is 1890 bytes vs DM7's 1785 — there may be 105 extra bytes from additional features (more sends, more dynamics units, etc.). HPF likely stays at the same position.

### What needs calibration

Same as TF: HPF On/Off, HPF frequency, EQ, dynamics offsets are unverified.

**Recommended approach:**

1. Write skeleton parser with Name/Color extraction.
2. Try DM7's HPF offsets (134/135/139) directly — there's a good chance they're the same.
3. Write a probe script `tools/rivage_offset_probe.py` to dump bytes at candidate offsets.
4. To verify: look for uint32 LE values that look like frequencies (÷10 = 20–20000 Hz) near offset 134. Also check if the byte at 134 is 0 or 1 (HPF On/Off).
5. If DM7 offsets don't match, request calibration file: user opens RIVAGE Editor, sets ch1 HPF ON 200Hz, saves as `samples/rivage_hpf_calibration.RIVAGEPM`.

### Deliverable

A working `engine/parsers/yamaha_rivage.py` that:
1. Detects `.RIVAGEPM` files (same MBDF magic)
2. Extracts Name, Color per channel
3. Attempts HPF extraction (DM7 offsets as first guess, documented in code)
4. Skips EQ/dynamics until calibration files available
5. At least 5 tests in `engine/tests/test_yamaha_rivage_parser.py`

Source console string: `"yamaha_rivage_pm"`

---

## File detection / routing

Both new parsers need to be wired into the engine's routing layer. Check how `engine/` routes files to parsers (likely in `engine/main.py` or an `engine/router.py`). The detection can be by file extension:
- `.tff` → `yamaha_tf.parse()`
- `.RIVAGEPM` → `yamaha_rivage.parse()`

---

## Do NOT do

- Do not modify the DM7 parser or its tests.
- Do not touch CL/QL or DiGiCo parsers.
- Do not fabricate HPF/EQ/dynamics values — if an offset is uncertain, set the field to a default and log it in `dropped_parameters`.
- Do not create documentation files.

---

## Tools available

```bash
# Probe any MBDF file
python tools/dm7_offset_probe.py samples/somefile.dm7f

# Run all tests
cd engine && [python] -m pytest tests/ -q

# Git
/mingw64/bin/git add ... && /mingw64/bin/git commit -m "..."
```

Python: `/c/Users/grego/AppData/Local/Microsoft/WindowsApps/python.exe`
