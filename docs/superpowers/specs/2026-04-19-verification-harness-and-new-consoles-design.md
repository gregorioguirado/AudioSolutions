# Design Spec: Verification Harness Extensions + New Consoles
**Date:** 2026-04-19  
**Status:** Approved for implementation

---

## 1. What We're Building

Three things in one sprint:

1. **Extend the verification harness** to cover EQ, gate, and compressor parameters — currently only name/color/HPF/muted are checked after round-trip. Add a fidelity score and surface results to the user inside the app.
2. **Yamaha QL parser + writer** — same binary format as CL, minimal new work, expands supported consoles.
3. **A&H dLive parser skeleton** — XML-based format; structure specced here, calibration blocked on sample `.AHsession` file.

---

## 2. Verification Harness Extensions

### 2.1 Current State

`engine/verification/harness.py` (353 lines) already exists and is hooked non-blockingly into `translator.translate()`. It re-parses the output file and diffs against the source `ShowFile`. But it only checks:

- `channel.name`
- `channel.color`
- `channel.input_patch`
- `channel.hpf_enabled`
- `channel.hpf_frequency`
- `channel.muted`

EQ bands, gate, and compressor are entirely unchecked. There are no YAML fixture baselines for real show files. The fidelity result is logged but never returned to the user.

### 2.2 L1 — Parse Gate (extend, don't rebuild)

The harness already re-parses. What's missing: **the re-parse failure needs to be surfaced in `TranslationResult`**, not just logged. If re-parse fails, `TranslationResult.parse_gate_passed = False`. The API returns this to the frontend. The frontend blocks download with an error — not a warning.

### 2.3 L2 — Field Coverage Report (extend harness parameter checks)

Add to `verify_translation()` in `harness.py`:

**EQ bands (4 bands per channel):**
- `eq_band[n].enabled`
- `eq_band[n].frequency` — tolerance ±1 Hz acceptable (rounding)
- `eq_band[n].gain` — tolerance ±0.01 dB
- `eq_band[n].q` — tolerance ±0.001
- `eq_band[n].band_type` — exact match; approximations logged separately

**Gate:**
- `gate.enabled`
- `gate.threshold` — tolerance ±0.01 dBFS
- `gate.attack` — tolerance ±1 ms
- `gate.hold` — tolerance ±1 ms
- `gate.release` — tolerance ±1 ms

**Compressor:**
- `compressor.enabled`
- `compressor.threshold` — tolerance ±0.01 dBFS
- `compressor.ratio` — tolerance ±0.01
- `compressor.attack` — tolerance ±1 ms
- `compressor.release` — tolerance ±1 ms
- `compressor.makeup_gain` — tolerance ±0.01 dB (skip check if source value is None — known RIVAGE gap)

Known untranslatable fields (log as dropped, never fail check):
- `gate.hold` → DiGiCo SD (no hold parameter)
- `compressor.knee_type` → all targets (brand-specific DSP)
- RIVAGE `compressor.makeup_gain` → not yet calibrated

### 2.4 L3 — Fidelity Score

Add `FidelityScore` to `HarnessResult`:

```python
@dataclass
class FidelityScore:
    names: float        # % channels with name match
    hpf: float          # % channels with HPF match (enabled + freq)
    eq: float           # % EQ band checks that passed (across all channels × 4 bands)
    gate: float         # % gate parameter checks that passed
    compressor: float   # % compressor parameter checks that passed
    overall: float      # weighted average: names 20%, hpf 20%, eq 20%, gate 20%, comp 20%
```

Computation: for each field group, `passed_checks / total_checks * 100`. Fields that are `None` in both source and target are excluded from the denominator (not a failure — channel just doesn't use that feature).

### 2.5 L4 — CI Regression Lock (fixture suite)

Add YAML fixture baselines for every sample file in `samples/`. Each fixture captures the fields that should survive round-trip for that specific file. Stored in `engine/verification/fixtures/`.

Fixture format (existing pattern, just more files):
```yaml
channel_count: 72
channels:
  - id: 1
    name: "KICK"
    hpf_enabled: true
    hpf_frequency: 80
    gate_threshold: -40.0
    compressor_threshold: -18.0
    compressor_ratio: 4.0
```

Add a pytest parametrize test that runs all fixtures in `engine/verification/fixtures/` automatically — new fixtures get tested without touching test code.

### 2.6 L5 — Verify Before Doors UX Gate

Backend: `TranslationResult` already carries `dropped_parameters` and will now carry `FidelityScore`. No backend changes needed for L5.

Frontend (`engine/main.py` API response): add `fidelity_score` and `parse_gate_passed` to the JSON response alongside the existing `translated_parameters` / `dropped_parameters`.

Frontend UX (outside the current sprint — spec only):  
Before download is enabled, show the coverage summary. If any fields are dropped, list them explicitly. Require the engineer to check a box: *"I will load this file on the console and verify before the show."* The download button is disabled until checked. This is the liability gate the council mandated.

### 2.7 What Does Not Change

- The non-blocking hook in `translator.py` stays. Harness failures never raise — they surface in `TranslationResult`.
- `engine/report.py` (PDF) — no changes this sprint. The PDF already shows translated/approximated/dropped.
- Writers — no changes this sprint.

---

## 3. Yamaha QL Parser + Writer

### 3.1 Format

QL show files use the **identical binary format** as CL show files (`.CLF` / `.CLE`). Same MBDF structure, same offsets confirmed in handover. The difference is channel count and console model metadata.

| Console | Channels | Model string |
|---|---|---|
| CL5 | 72 | `CL5` |
| QL5 | 64 | `QL5` |
| QL1 | 32 | `QL1` |

### 3.2 Parser

Reuse `_parse_yamaha_auto()` in `translator.py` — it already auto-detects ZIP vs binary and dispatches to `yamaha_cl_binary.py`. The QL parser is a thin wrapper that sets `console_model = "yamaha_ql"` and passes through to the same binary parser.

```python
# engine/parsers/yamaha_ql.py
def parse_yamaha_ql(data: bytes) -> ShowFile:
    from .yamaha_cl_binary import parse_yamaha_cl_binary
    show = parse_yamaha_cl_binary(data)
    show.console_model = "yamaha_ql"
    return show
```

Register in `translator.py`:
```python
PARSERS["yamaha_ql"] = parse_yamaha_ql
```

### 3.3 Writer

`write_yamaha_cl_binary()` uses a `cl5_empty.CLF` template. For QL we need a QL-specific empty template — the binary structure is the same but the template must report the correct model name internally.

Once a QL template is available (sourced from QL Editor after install):
1. Save an empty show from QL Editor as `ql5_empty.CLF`
2. Drop in `engine/writers/templates/`
3. Add `write_yamaha_ql_binary()` in `engine/writers/yamaha_ql_binary.py` — copy of the CL binary writer pointing at the QL template

Register in `translator.py`:
```python
WRITERS["yamaha_ql"] = write_yamaha_ql_binary
```

**Blocked on:** QL Editor install + empty template file. Parser can be written and tested now; writer is blocked.

### 3.4 Tests

- `engine/tests/test_yamaha_ql_parser.py` — verify channel count, names, HPF, EQ parse correctly from a QL sample file
- `engine/tests/test_yamaha_ql_binary_writer.py` — round-trip: parse QL → write → re-parse → compare (once template available)
- Fixture: `engine/verification/fixtures/ql5_sample.yaml`

---

## 4. A&H dLive Parser

### 4.1 Format

A&H dLive show files (`.AHsession`) are **XML-based**, structured as a folder/zip containing XML documents. Parsing approach: Python `xml.etree.ElementTree` (same as DiGiCo and Yamaha CL XML parsers). No binary struct unpacking needed.

### 4.2 Expected XML Structure (to be calibrated)

Based on A&H dLive architecture knowledge, the show file likely contains:

```xml
<MixRack>
  <Inputs>
    <Input id="1">
      <Name>KICK</Name>
      <Color>RED</Color>
      <HPF>
        <Enable>true</Enable>
        <Frequency>80</Frequency>
      </HPF>
      <EQ>
        <Band id="1">
          <Enable>true</Enable>
          <Frequency>100</Frequency>
          <Gain>-3.0</Gain>
          <Q>0.707</Q>
          <Type>LowShelf</Type>
        </Band>
        ...
      </EQ>
      <Gate>...</Gate>
      <Compressor>...</Compressor>
    </Input>
  </Inputs>
</MixRack>
```

**All field paths and attribute names must be calibrated against a real `.AHsession` file before implementation.** The structure above is an informed estimate only.

### 4.3 Parser Skeleton

```python
# engine/parsers/ah_dlive.py
import zipfile, xml.etree.ElementTree as ET
from ..models.universal import ShowFile, Channel

def parse_ah_dlive(data: bytes) -> ShowFile:
    # AHsession files are ZIP archives containing XML
    # TODO: calibrate XML paths against real sample file
    raise NotImplementedError("Pending calibration against .AHsession sample file")
```

Register in `translator.py`:
```python
PARSERS["ah_dlive"] = parse_ah_dlive
```

**Blocked on:** `.AHsession` sample file from dLive Director install.

### 4.4 Writer

A&H dLive writer (`engine/writers/ah_dlive.py`) follows the DiGiCo pattern — generate XML from the universal model, zip it into the session structure.

Also blocked on sample file (need to understand the ZIP/folder structure).

### 4.5 Color Mapping

A&H dLive uses named colors. Mapping to universal `ChannelColor` enum must be calibrated from the sample file. Approximate expected mapping:

| dLive | Universal |
|---|---|
| `Red` | `RED` |
| `Green` | `GREEN` |
| `Blue` | `BLUE` |
| `Yellow` | `YELLOW` |
| `Purple` / `Violet` | `PURPLE` |
| `White` | `WHITE` |
| `Cyan` / `Teal` | `CYAN` |

### 4.6 Known dLive Limitations (pre-calibration)

- dLive uses 96 input channels (dLive S7000) down to 48 (C1500) — channel count varies by model
- dLive has 6-band PEQ per channel (vs 4 bands in universal model) — extra bands logged as dropped
- dLive gate has `Key Filter` (sidechain HPF/LPF) — no universal model equivalent, dropped
- dLive compressor has `Ratio` as a stepped value — map to nearest float

---

## 5. Execution Order

1. **Extend `harness.py`** — add EQ/gate/comp checks + FidelityScore (unblocked)
2. **Add `fidelity_score` + `parse_gate_passed` to `TranslationResult`** (unblocked)
3. **Fixture suite** — add YAML baselines for all sample files + parametrize test (unblocked)
4. **Yamaha QL parser** — thin wrapper, register in PARSERS (unblocked)
5. **A&H dLive parser skeleton** — file + NotImplementedError, register in PARSERS (unblocked)
6. **Yamaha QL writer + template** — blocked on QL Editor install
7. **A&H dLive parser calibration** — blocked on `.AHsession` sample file
8. **A&H dLive writer** — blocked on sample file

Steps 1–5 can run in parallel across agents. Steps 6–8 are blocked on external assets.

---

## 6. Files Changed / Created

| File | Action |
|---|---|
| `engine/verification/harness.py` | Extend: add EQ/gate/comp checks, FidelityScore |
| `engine/translator.py` | Extend: expose `parse_gate_passed` + `fidelity_score` in result |
| `engine/verification/fixtures/*.yaml` | Create: one fixture per sample file |
| `engine/tests/verification/test_harness.py` | Extend: parametrize fixture suite |
| `engine/parsers/yamaha_ql.py` | Create: thin wrapper over CL binary parser |
| `engine/parsers/ah_dlive.py` | Create: skeleton with NotImplementedError |
| `engine/writers/yamaha_ql_binary.py` | Create: copy of CL binary writer (blocked on template) |
| `engine/writers/ah_dlive.py` | Create: skeleton (blocked on sample file) |
| `engine/writers/templates/ql5_empty.CLF` | Create: sourced from QL Editor (blocked) |

No existing files deleted. No existing tests removed.
