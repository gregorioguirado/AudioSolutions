# Multi-Console Expansion Plan for Showfier

**Date:** 2026-04-10
**Status:** Planning
**Prerequisite:** Yamaha CL5 binary parser complete, universal model operational, CL-to-DiGiCo translation working (synthetic fixtures)

---

## 1. Console Priority Ranking

### Scoring Criteria

Each console family is scored across four dimensions (1-5 scale):

| Dimension | What it measures |
|-----------|-----------------|
| Market demand | How often touring engineers encounter this console and need translation to/from it |
| Reverse-engineering feasibility | How approachable the file format is (XML = easy, proprietary binary = hard, shared family = batch win) |
| Strategic value | Competitive positioning vs. ConsoleFlip, coverage of high-value translation pairs |
| Sample file availability | Whether we already have real files or need to acquire them |

### Priority Ranking

| Priority | Console Family | Market | Feasibility | Strategic | Samples | Total | Reasoning |
|----------|---------------|--------|-------------|-----------|---------|-------|-----------|
| **1** | **Yamaha MBDF family (DM7, TF, RIVAGE PM)** | 4 | 5 | 4 | 5 | **18** | We already have real files for all three. They share the `#YAMAHA MBDFProjectFile` header — cracking one likely cracks the family. TF series is the most popular "budget pro" console worldwide. RIVAGE PM is Yamaha's flagship touring platform. This is the fastest path to broad Yamaha ecosystem coverage. |
| **2** | **DiGiCo SD/Quantum (real .show files)** | 5 | 3 | 5 | 2 | **15** | DiGiCo dominates A-list touring and festivals. The CL-to-DiGiCo pair is the single most demanded translation path. We currently only handle synthetic XML — we need to parse real `.show` files to ship a credible product. Requires acquiring real show files. |
| **3** | **Allen & Heath dLive/Avantis** | 4 | 3 | 5 | 1 | **13** | Fastest-growing brand in live sound. ConsoleFlip only does A&H intra-brand conversions — Showfier doing A&H cross-brand (A&H-to-Yamaha, A&H-to-DiGiCo) is a direct competitive differentiator. No sample files yet; need to acquire from the founder's network. |
| **4** | **Yamaha QL series** | 3 | 5 | 3 | 4 | **15** | QL shares the same CLF/CLE binary format as CL — our existing parser likely works with zero or minimal changes. The QL is extremely common in corporate, worship, and mid-tier touring. Nearly free to add. Score adjusted down on strategic value since CL parser already covers most of this ground. |
| **5** | **Midas PRO series** | 2 | 2 | 3 | 1 | **8** | Declining market share but massive legacy install base (PRO2, PRO6, PRO9). Still common in rental inventories. Format is proprietary binary — harder to crack. No sample files. Lower priority because the user base is shrinking. |
| **6** | **SSL Live** | 2 | 2 | 3 | 1 | **8** | Premium niche brand, growing in broadcast and theater. Small user base but high willingness to pay. No sample files, format unknown. Worth doing eventually for completeness but not urgent. |
| **7** | **Avid VENUE S6L** | 3 | 1 | 4 | 1 | **9** | Dominant in North American touring. Very high strategic value for translation pairs. However, VENUE files are notoriously complex (database-like format, tightly coupled to system configuration). Likely the hardest format to crack. No sample files. |
| **8** | **Behringer X32/Wing** | 2 | 3 | 2 | 1 | **8** | Massive install base but primarily in budget/worship/corporate markets where users are less likely to pay for translation tools. X32 format is relatively well-documented by the community. Low strategic priority — these users overlap less with our target persona. |

### Recommended Execution Order

```
Phase 1 (Immediate):     Yamaha MBDF family (DM7, TF, RIVAGE PM) + QL validation
Phase 2 (Next):          DiGiCo real .show parser
Phase 3 (Following):     Allen & Heath dLive/Avantis
Phase 4 (Future):        Midas PRO, SSL Live, Avid VENUE, Behringer X32/Wing
```

**Rationale:** Phase 1 is the fastest win — we have all the sample files, the formats share a common container, and it triples our Yamaha coverage overnight. Phase 2 completes the MVP's core promise (Yamaha-to-DiGiCo with real files). Phase 3 is the competitive differentiator against ConsoleFlip.

---

## 2. Format Families (Batch Wins)

### Family A: Yamaha CL/QL Binary (.CLF/.CLE)

| Property | Value |
|----------|-------|
| Consoles | CL1, CL3, CL5, QL1, QL5 |
| File types | `.CLF` (console USB save), `.CLE` (CL Editor / QL Editor desktop save) |
| Format | Proprietary binary, MEMAPI scene markers, fixed-offset parameter tables |
| Status | **CRACKED** — full parser built (`engine/parsers/yamaha_cl_binary.py`) |
| Batch win | QL uses the same format as CL with minor differences (fewer input channels, different format identifier byte at 0x08). Validating the existing parser against a QL file should require minimal effort. |

### Family B: Yamaha MBDF Container (.dm7f, .tff, .RIVAGEPM)

| Property | Value |
|----------|-------|
| Consoles | DM7 (`.dm7f`), TF1/TF3/TF5 (`.tff`), RIVAGE PM3/PM5/PM7/PM10 (`.RIVAGEPM`) |
| File types | Console-specific extensions, all starting with `#YAMAHA MBDFProjectFile` |
| Format | MBDF container with model identifier at byte 0x24 (`DM7`, `TF`, `Rivage`), followed by version info, then `#MMS FIE` section markers |
| Status | **NOT CRACKED** — header structure identified, internal layout unknown |
| Batch win | All three share the same container format. The header structure is: `#YAMAHA MBDFProjectFile` (22 bytes) + null + padding to 0x24 + model name + version + hash/checksum + `#MMS FIE` sections. Cracking the MBDF container parser unlocks the shared structure; per-console differences are likely limited to channel counts, parameter ranges, and section offsets. **Cracking DM7 likely gives us TF and RIVAGE PM with minimal additional effort.** |

**Key observation from file headers:**
```
DM7:    ...DM7\x00...V\x01I...#MMS FIE
TF:     ...TF\x00\x00...V\x042...#MMS FIE
RIVAGE: ...Rivage\x00...V\x07\x00...#MMS FIE
```
The `V` byte followed by version numbers differs per model, but the overall structure is consistent. The `#MMS FIE` marker (likely "MMS FILE" or similar) appears in all three at approximately the same relative position.

**Additional context:** Yamaha's own Console File Converter (v6.1.0, May 2025) supports conversion between RIVAGE PM, CL/QL, PM5D, M7CL, LS9, and DM7 — confirming these formats share enough structural commonality for Yamaha's own tooling to bridge them. Our MBDF research will benefit from this knowledge.

### Family C: DiGiCo SD/Quantum (.show)

| Property | Value |
|----------|-------|
| Consoles | SD7, SD7T, SD10, SD12, SD5, SD9, Quantum 225/338/5/7, T series |
| File types | `.show` |
| Format | Likely XML-based (DiGiCo has historically used XML), possibly compressed/packaged |
| Status | **SYNTHETIC ONLY** — we have a writer that produces valid-looking XML, but we have never parsed a real `.show` file |
| Batch win | All SD-series and Quantum consoles share the same software platform. A single `.show` parser should cover the entire DiGiCo range. The T series (theatre) may have additional data structures but the core channel/processing format will be shared. DiGiCo's own SD Convert tool confirms intra-family compatibility. |

### Family D: Allen & Heath dLive/Avantis (.show or export format)

| Property | Value |
|----------|-------|
| Consoles | dLive (C1500, C2500, C3500 + DM0, DM32, DM48, DM64 MixRacks), Avantis (Solo, Duo), SQ series |
| File types | Unknown — need to investigate. dLive Director exports `.allfiles` or similar. SQ uses `.sq` files. |
| Format | Unknown — need real files to determine. dLive Director offers CSV export of channel names/patch which suggests the native format may be binary or database-based. |
| Status | **NO FILES, NO RESEARCH** |
| Batch win | dLive and Avantis run the same XCVI processing engine with the same firmware. Their show file formats are very likely identical or near-identical, differing only in surface layer count and I/O configuration. ConsoleFlip already handles dLive-to-Avantis conversion, confirming format similarity. SQ is a separate (simpler) platform and may have a different format. |

### Family E: Other Brands

| Console | Format | Notes |
|---------|--------|-------|
| Midas PRO (PRO2/6/9/X/XL8) | Proprietary binary (`.sho` files) | Midas PRO Offline Editor is the source. Legacy platform, declining. |
| SSL Live (L100/L200/L300/L500/L550) | Unknown | SOLSA software is the editor. Small market but premium. |
| Avid VENUE S6L | Proprietary (`.vnue` or similar) | Database-like format, tightly coupled to VENUE software. Hardest to crack. |
| Behringer X32/Wing | OSC-based, partially documented | X32 Edit exports `.scn` files. Community has partially documented the format. Wing uses `.wing` files. |

---

## 3. What We Need From the User Per Console

### Standard Calibration File Set (7 Files)

This is the proven methodology from the CL5 reverse-engineering. For each console family, the user needs to produce these files using the console's offline editor software:

| # | File Name Pattern | What to Set | Why |
|---|-------------------|-------------|-----|
| 1 | `{console} empty calibration.{ext}` | Default new show, no changes | Baseline for diffing |
| 2 | `{console} calibration HPF-EQ.{ext}` | Ch1: HPF ON at 200Hz, EQ Band 1 = 200Hz/+6dB, Band 2 = 800Hz/-4dB, Band 3 = 3kHz/+3dB, Band 4 = 8kHz/-2dB | Maps HPF and all 4 EQ bands in one file |
| 3 | `{console} calibration dynamics.{ext}` | Ch1: Gate ON, threshold -30dB, attack 1ms, hold 100ms, release 200ms; Comp ON, threshold -20dB, ratio 4:1, attack 5ms, release 100ms, makeup +6dB | Maps gate + compressor parameters |
| 4 | `{console} calibration fader-pan-mute.{ext}` | Ch1: fader at -10dB, pan hard left, channel OFF/muted | Maps fader level, pan position, mute state |
| 5 | `{console} calibration mix-sends.{ext}` | Ch1: Send to Mix 1 at 0dB PRE, Send to Mix 2 at -6dB POST | Maps mix bus send level, pre/post routing |
| 6 | `{console} calibration names-colors.{ext}` | Ch1 named "TESTNAME", Ch2 named "SECONDCH", Ch1 color = red, Ch2 color = blue | Maps channel name encoding and color palette |
| 7 | `{console} calibration DCA-groups.{ext}` | Ch1 assigned to DCA 1 and DCA 3, Ch1 assigned to Mute Group 2 | Maps DCA and mute group assignments |

### Per-Console-Family Requirements

#### Yamaha MBDF Family (DM7, TF, RIVAGE PM)

| Item | DM7 | TF | RIVAGE PM |
|------|-----|----|-----------|
| Editor software | DM7 Editor (free download from Yamaha) | TF Editor (free download) | RIVAGE PM Editor (free download) |
| File extension | `.dm7f` | `.tff` | `.RIVAGEPM` |
| Calibration files needed | 7 (standard set) | 7 (standard set) | 7 (standard set) |
| Real console save needed? | Nice to have but editor-only should work | Nice to have but editor-only should work | Nice to have but editor-only should work |
| Sample files we already have | `Bertoleza Sesi Campinas.dm7f` (real show) | `DOM CASMURRO 2.tff` (real show) | `RIVAGE EMI 21.3.RIVAGEPM` (real show) |
| Notes | 72 input channels (same as CL). Likely closest MBDF cousin to CL format. **Start here.** | 40 input channels (TF5) / 32 (TF3) / 16 (TF1). Simpler channel strip than CL. | Up to 144 input channels (PM10). Most complex Yamaha console. May have additional sections for DSP engines, Silk processing. |

**Priority within family:** DM7 first (closest to CL in channel count and feature set), then TF (simpler, huge installed base), then RIVAGE PM (most complex, smallest user base of the three).

#### Yamaha QL Series

| Item | Details |
|------|---------|
| Editor software | QL Editor (free download from Yamaha) |
| File extension | `.CLF` / `.CLE` (same as CL) |
| Calibration files needed | 2-3 (just need to confirm existing CL parser works — empty + one full calibration) |
| Real console save needed? | One real QL show file for validation |
| Sample files we have | None labeled as QL, but format is identical to CL |
| Notes | QL uses the same binary format as CL. The format identifier byte at offset 0x08 will differ. Channel count is 64 (QL5) or 32 (QL1) vs. CL's 72. The existing parser should work with a channel count adjustment. |

#### DiGiCo SD/Quantum

| Item | Details |
|------|---------|
| Editor software | SD Offline Editor (free download from DiGiCo) |
| File extension | `.show` |
| Calibration files needed | 7 (standard set) — but also need to examine the raw file format first (open in a text editor to check if it's XML, binary, or packaged) |
| Real console save needed? | Yes, critically. Our current DiGiCo parser only handles synthetic XML. We need real `.show` files from actual consoles or the offline editor to understand the true format. |
| Sample files we have | None (only synthetic XML test fixtures generated by our own writer) |
| Notes | DiGiCo Offline Editor is free but requires registration. The founder should create calibration files in the offline editor AND ideally obtain 1-2 real show files from colleagues who use DiGiCo. This is the biggest gap blocking MVP credibility. |

#### Allen & Heath dLive/Avantis

| Item | Details |
|------|---------|
| Editor software | dLive Director (free download), Avantis Offline (free download) |
| File extension | Unknown — need to investigate what dLive Director exports |
| Calibration files needed | 7 (standard set) + format investigation files (save empty show, examine raw bytes) |
| Real console save needed? | Yes — dLive Director saves may differ from real console saves |
| Sample files we have | None |
| Notes | dLive Director supports CSV export of names/patch, which is useful as a reference but not the full show file. Need to determine the native export format first. ConsoleFlip has already reverse-engineered this format for intra-A&H conversion, so it's proven doable. The SQ series uses a separate, simpler format and should be treated as a sub-project. |

#### Midas PRO / SSL Live / Avid VENUE (Phase 4)

| Console | Editor | File Type | Notes |
|---------|--------|-----------|-------|
| Midas PRO | Midas PRO Offline Editor | `.sho` (unconfirmed) | Editor is free. Legacy platform with shrinking user base. Only pursue if there's clear demand. |
| SSL Live | SOLSA | Unknown | SOLSA may require a license. Small market. Low priority unless a customer specifically requests it. |
| Avid VENUE S6L | VENUE Offline | `.vnue` (unconfirmed) | Most complex format. Database-like. Only pursue with significant demand. |

---

## 4. Parallelization Strategy

### Overview

The user wants to accelerate console support by running multiple reverse-engineering efforts in parallel using independent Claude agents. This is feasible because each console's format is independent — agents don't need to share state.

### Prerequisites (Must Be Done Sequentially)

Before spawning parallel agents, these must be in place:

1. **Universal data model is stable** — All agents write parsers that output to the same `ShowFile` dataclass. The current model (`engine/models/universal.py`) must be reviewed and, if needed, extended to cover fields that new consoles may introduce (e.g., RIVAGE PM's Silk/Silk+ processing, additional aux bus types, matrix routing). Do this ONCE, before parallelization.

2. **Parser template document** — Create a standardized "how to reverse-engineer a console format" methodology document based on the CL5 experience. Each agent gets this as context. It should include:
   - The calibration file diffing technique
   - How to identify parameter offsets
   - How to derive encoding formulas (log scales, signed values, etc.)
   - How to validate against real show files
   - The expected output format (parser module with `parse_{console}(filepath) -> ShowFile`)

3. **Calibration files are produced** — The user creates calibration file sets for all target consoles. This is the bottleneck — the user must do this manually using each console's editor software. However, the user can produce calibration files for multiple consoles simultaneously since each editor is independent.

### Parallel Workflow

```
STEP 1: User Preparation (Parallelizable by the user)
─────────────────────────────────────────────────────
User installs editors:    DM7 Editor  |  TF Editor  |  RIVAGE Editor  |  DiGiCo Offline  |  dLive Director
User creates cal files:   7 files     |  7 files    |  7 files        |  7 files         |  7 files
User provides to agents:  Upload to samples/{console}/

Timeline: 1-2 days (user can do all editors in parallel, ~30 min per editor)


STEP 2: Agent Spawning (Parallel — One Agent Per Console Family)
───────────────────────────────────────────────────────────────
Each agent receives:
  - The calibration files for its assigned console
  - The parser template methodology document
  - The universal data model definition (engine/models/universal.py)
  - The CL5 binary parser as a reference implementation (engine/parsers/yamaha_cl_binary.py)
  - The CL5 format spec as an example of expected output (docs/research/yamaha-clf-format.md)
  - Any real show files we have for that console (from samples/)

Agent A: MBDF Family      Agent B: DiGiCo        Agent C: A&H dLive
──────────────────        ─────────────           ────────────────
1. Examine file headers   1. Examine .show format  1. Examine file format
2. Diff empty vs cal      2. Determine if XML/bin  2. Diff empty vs cal
3. Map MBDF container     3. Diff empty vs cal     3. Map parameters
4. Map DM7 params         4. Map parameters        4. Build parser
5. Build DM7 parser       5. Build parser          5. Test vs real files
6. Test vs real file      6. Test vs real files     6. Produce format spec
7. Adapt for TF           7. Produce format spec   7. Deliver parser module
8. Adapt for RIVAGE PM
9. Produce format spec
10. Deliver parser modules

Timeline per agent: 1-3 sessions depending on format complexity


STEP 3: Integration (Sequential — Main Agent)
─────────────────────────────────────────────
1. Review each delivered parser module
2. Run each parser against available real show files
3. Validate output against expected parameter values
4. Wire each parser into translator.py (add to PARSERS dict)
5. Add console options to web UI dropdown
6. Run full integration tests (parse → universal → write → verify)

Timeline: 1 session


STEP 4: Writer Development (Parallelizable After Parsers Done)
─────────────────────────────────────────────────────────────
Once we can PARSE a format, writing it requires understanding:
- File structure (headers, section layout, checksums)
- Parameter encoding (reverse of parsing)
- Minimum viable file (what sections are required for the console to accept the file)

Writer agents can run in parallel, one per console family.

Timeline: 1-2 sessions per writer
```

### Agent Task Specification Template

Each agent should receive a task brief like this:

```
TASK: Reverse-engineer {CONSOLE} show file format
INPUTS:
  - Calibration files: samples/{console}/
  - Real show file(s): samples/{real_file}
  - Reference parser: engine/parsers/yamaha_cl_binary.py
  - Reference format spec: docs/research/yamaha-clf-format.md
  - Universal model: engine/models/universal.py

DELIVERABLES:
  1. Format specification document: docs/research/{console}-format.md
     - File structure (header, sections, markers)
     - Per-channel parameter offsets and encoding formulas
     - Validation results against real show files
  2. Parser module: engine/parsers/{console}.py
     - Function: parse_{console}(filepath: Path) -> ShowFile
     - Must populate: channel names, colors, input patch, HPF, EQ (4 bands),
       gate, compressor, fader, pan, mute, DCA assignments, mix bus sends
     - Must log dropped/approximated parameters to ShowFile.dropped_parameters
  3. Test file: engine/tests/test_{console}_parser.py
     - At least one test using a real show file
     - Parameter spot-checks (verify known values parse correctly)

CONSTRAINTS:
  - Do NOT modify universal.py without flagging the need for model extension
  - Do NOT modify other parsers or shared code
  - Output must match the ShowFile dataclass exactly
  - All frequency/gain values must be mathematically precise
  - Log any parameters that cannot be mapped as dropped
```

### Bottleneck Analysis

| Step | Bottleneck | Mitigation |
|------|-----------|------------|
| Calibration file creation | User must do this manually per editor | User can run multiple editors simultaneously; provide a clear step-by-step guide |
| Acquiring real DiGiCo .show files | We have zero real DiGiCo files | Founder needs to reach out to DiGiCo-using colleagues. This is critical path. |
| Acquiring A&H files | We have zero A&H files | Same — founder's network. Less urgent than DiGiCo since A&H is Phase 3. |
| MBDF container complexity | Unknown internal structure may be harder than CL binary | We have 3 real MBDF files to examine. Start with DM7 (closest to CL in scope). |
| Writer development | Each writer needs format knowledge from parsing phase | Writers can only start after parsers are verified. This is inherently sequential per format. |

---

## 5. In-Brand Conversion Support

### Why This Matters

The user specifically wants CL-to-TF, CL-to-QL, CL-to-DM7, etc. This means Showfier is not just a cross-brand translator — it's also the best intra-Yamaha translator, better than Yamaha's own Console File Converter because:

1. **Yamaha's tool doesn't cover all pairs** — it supports RIVAGE PM, CL/QL, PM5D, M7CL, LS9, DM7 but not all directions equally
2. **Yamaha's tool doesn't produce translation reports** — engineers don't know what was dropped
3. **Showfier can handle parameter approximation with documentation** — engineers see exactly what changed

### The Parse-Universal-Write Architecture

```
Source File ─→ Parser ─→ Universal Model ─→ Writer ─→ Target File

Examples:
  CL5 .CLF  ─→ yamaha_cl_binary.parse() ─→ ShowFile ─→ yamaha_tf.write() ─→ .tff
  DM7 .dm7f ─→ yamaha_mbdf.parse()      ─→ ShowFile ─→ yamaha_cl.write() ─→ .CLF
  CL5 .CLF  ─→ yamaha_cl_binary.parse() ─→ ShowFile ─→ digico_sd.write() ─→ .show
```

This means for N console formats, we need N parsers and N writers, giving us N x (N-1) translation pairs. With 6 formats (CL, DM7, TF, RIVAGE, DiGiCo, A&H), that's 30 translation directions.

### Writer Requirements

For each console format, a writer must:

1. **Produce a file the console/editor will accept** — this is the hard part. The file must have correct headers, checksums, section structure, and valid parameter ranges.
2. **Map universal model values back to console-specific encoding** — reverse of parsing (e.g., Hz back to Yamaha's log-scale byte, dB back to signed 16-bit threshold).
3. **Handle parameter range differences** — if the source console has 72 channels and the target has 40, the writer must truncate gracefully and log what was dropped.
4. **Include default values for unset parameters** — if the universal model doesn't specify a parameter the target console requires, use the console's default.

### Writer Development Strategy

| Writer | Approach | Difficulty |
|--------|----------|------------|
| **Yamaha CL binary (.CLF/.CLE)** | Start from an empty calibration file as a template. Overwrite parameter bytes at known offsets. This avoids having to construct the entire binary structure from scratch. | Medium-Hard — requires understanding which bytes are checksums/CRC vs. data, and whether the console validates file integrity on load. |
| **Yamaha MBDF (.dm7f, .tff, .RIVAGEPM)** | Same template-based approach: start from an empty file saved by the editor, overwrite parameter sections. | Medium — depends on whether MBDF files have checksums. |
| **DiGiCo SD (.show)** | If the format is XML, writing is straightforward — construct the XML tree. If it's packaged/compressed, need to understand the packaging. | Easy (if XML) to Medium (if packaged) |
| **Allen & Heath dLive** | Unknown until we analyze the format. | Unknown |

### Template-Based Writer Pattern

For binary formats, the safest writer approach is:

```python
def write_yamaha_cl_binary(show: ShowFile) -> bytes:
    """Write a ShowFile to Yamaha CL binary format.

    Strategy: Load a known-good empty CLF template file,
    then overwrite parameter bytes at mapped offsets.
    """
    # 1. Load empty template (bundled with the engine)
    template = load_template("yamaha_cl_empty.CLF")

    # 2. Find the first MEMAPI scene marker
    scene_offset = find_memapi(template)

    # 3. Write channel names into name tables
    for ch in show.channels:
        write_name(template, scene_offset, ch.id - 1, ch.name)

    # 4. Write HPF, EQ, dynamics, fader, pan, mute, DCA...
    for ch in show.channels:
        write_hpf(template, scene_offset, ch)
        write_eq(template, scene_offset, ch)
        write_gate(template, scene_offset, ch)
        write_compressor(template, scene_offset, ch)
        # ... etc

    # 5. Update any checksums if required

    return bytes(template)
```

This pattern requires:
- An empty template file per console model (saved from the editor, bundled with the engine)
- Reverse-mapped encoding functions (Hz to byte index, dB to threshold bytes, etc.)
- Checksum/CRC understanding (if the console validates file integrity)

### Current Writer Status

| Writer | Status | Format | Notes |
|--------|--------|--------|-------|
| Yamaha CL (XML) | Built | Synthetic ZIP+XML | `engine/writers/yamaha_cl.py` — produces synthetic XML in a ZIP. NOT a valid binary CLF/CLE. Sufficient for testing but not for real console import. |
| DiGiCo SD (XML) | Built | Synthetic XML | `engine/writers/digico_sd.py` — produces synthetic XML. May or may not be importable by real DiGiCo consoles. |
| Yamaha CL (binary) | **NOT BUILT** | Binary CLF/CLE | Required for in-brand translation. Template-based approach recommended. |
| All others | **NOT BUILT** | — | Blocked on parsing phase. |

### Priority for Writer Development

1. **DiGiCo SD writer (real format)** — validates our output against real console import. Critical for MVP launch.
2. **Yamaha CL binary writer** — enables CL-to-CL roundtrip testing and in-brand translation from other Yamaha models to CL.
3. **Yamaha MBDF writers (DM7, TF, RIVAGE)** — enables full in-brand Yamaha coverage.
4. **A&H dLive writer** — enables cross-brand A&H support.

---

## 6. Timeline Estimates

### Assumptions

- "Session" = one focused Claude agent work session (2-4 hours of agent time)
- Calibration files are provided by the user before the agent session begins
- Estimates assume the agent has the reference parser, format spec, and universal model as context
- Real show files are available for validation

### Per-Console-Family Estimates

#### Yamaha MBDF Family (DM7 + TF + RIVAGE PM)

| Task | Effort | Dependencies |
|------|--------|-------------|
| MBDF container analysis (shared structure) | 1 session | Calibration files for DM7 |
| DM7 parser (first MBDF console) | 1-2 sessions | MBDF container analysis |
| DM7 parser validation vs. real file | 0.5 session | DM7 parser |
| TF parser (adapt from DM7) | 0.5-1 session | DM7 parser |
| RIVAGE PM parser (adapt from DM7) | 0.5-1 session | DM7 parser |
| Format spec documentation | 0.5 session | All parsers |
| **Total parsing** | **3-5 sessions** | |
| DM7 writer (template-based) | 1-2 sessions | DM7 parser + empty template file |
| TF writer | 1 session | TF parser + empty template file |
| RIVAGE PM writer | 1 session | RIVAGE parser + empty template file |
| **Total writing** | **3-4 sessions** | |
| **Grand total for MBDF family** | **6-9 sessions** | |

**Risk factor:** If the MBDF container uses encryption, compression, or complex checksums, add 2-3 sessions.

#### Yamaha QL Validation

| Task | Effort | Dependencies |
|------|--------|-------------|
| Test existing CL parser against QL file | 0.5 session | One real QL show file or QL Editor calibration files |
| Adjust channel count and format ID detection | 0.5 session | Test results |
| **Total** | **0.5-1 session** | |

This is the single fastest win — near-zero effort if the CL parser works as-is.

#### DiGiCo SD/Quantum (Real .show Files)

| Task | Effort | Dependencies |
|------|--------|-------------|
| Format investigation (determine if XML, binary, or packaged) | 0.5 session | At least 1 real .show file |
| Calibration file diffing and parameter mapping | 1-2 sessions | Calibration files from DiGiCo Offline Editor |
| Parser implementation | 1-2 sessions | Parameter mapping |
| Validation against real show files | 0.5-1 session | Real show files from working engineers |
| Writer implementation (update existing or rewrite) | 1-2 sessions | Parser + format understanding |
| Format spec documentation | 0.5 session | All above |
| **Total** | **4-7 sessions** | |

**Risk factor:** If `.show` files are binary rather than XML, difficulty increases significantly. If they're XML but with a custom schema, it's straightforward.

#### Allen & Heath dLive/Avantis

| Task | Effort | Dependencies |
|------|--------|-------------|
| Format investigation (completely unknown) | 1 session | At least 1 real show file + dLive Director export |
| Calibration file diffing and parameter mapping | 1-2 sessions | Calibration files + format knowledge |
| Parser implementation | 1-2 sessions | Parameter mapping |
| Avantis adaptation (if format differs) | 0.5-1 session | dLive parser |
| Validation against real show files | 0.5-1 session | Real show files |
| Writer implementation | 1-2 sessions | Parser + format understanding |
| Format spec documentation | 0.5 session | All above |
| **Total** | **5-8 sessions** | |

**Risk factor:** Completely unknown format. If binary with no obvious structure, could take longer. ConsoleFlip's existence proves it's crackable.

#### Each Additional Writer (Midas, SSL, Avid)

| Task | Effort | Dependencies |
|------|--------|-------------|
| Format investigation | 1 session | Real files |
| Full reverse-engineering + parser | 2-4 sessions | Calibration files |
| Writer | 1-2 sessions | Parser |
| **Total per console** | **4-7 sessions** | |

### Summary Timeline

| Phase | Consoles | Effort | Calendar Time (1 session/day) | Parallelizable? |
|-------|----------|--------|-------------------------------|-----------------|
| **Phase 1a** | QL validation | 0.5-1 session | 1 day | Independent |
| **Phase 1b** | MBDF parsing (DM7, TF, RIVAGE) | 3-5 sessions | 3-5 days | One agent |
| **Phase 2** | DiGiCo real .show | 4-7 sessions | 4-7 days | Parallel with Phase 1b |
| **Phase 3** | A&H dLive/Avantis | 5-8 sessions | 5-8 days | Parallel with Phase 2 |
| **Phase 4** | MBDF writers | 3-4 sessions | 3-4 days | After Phase 1b |
| **Phase 5** | DiGiCo + A&H writers | 2-4 sessions | 2-4 days | After Phase 2+3 |

**Best case with full parallelization:** Phases 1a+1b+2 run in parallel = ~7 days for parsing of all Yamaha + DiGiCo. Phase 3 overlaps. Writers follow. Total: ~2-3 weeks to support 7+ console models (CL, QL, DM7, TF, RIVAGE PM, DiGiCo SD, A&H dLive).

**Realistic case (accounting for user calibration file production, troubleshooting, and iteration):** 4-6 weeks to full multi-console support through Phase 3.

### Critical Path

```
User produces calibration files (1-2 days)
        │
        ├─→ Agent A: MBDF family (3-5 days) ─→ MBDF writers (3-4 days)
        │
        ├─→ Agent B: DiGiCo (4-7 days) ─→ DiGiCo writer (1-2 days)
        │
        └─→ Agent C: A&H dLive (5-8 days) ─→ A&H writer (1-2 days)
                                                      │
                                                      ▼
                                              Integration + testing (1-2 days)
                                                      │
                                                      ▼
                                              Web UI update (1 day)
                                                      │
                                                      ▼
                                              Ship multi-console Showfier
```

---

## 7. Translation Pair Matrix (Target State)

Once all Phase 1-3 consoles are supported, the translation matrix looks like this:

| FROM ↓ / TO → | CL/QL | DM7 | TF | RIVAGE | DiGiCo SD | A&H dLive |
|----------------|-------|-----|----|---------|-----------|-----------| 
| **CL/QL** | — | Yes | Yes | Yes | Yes | Yes |
| **DM7** | Yes | — | Yes | Yes | Yes | Yes |
| **TF** | Yes | Yes | — | Yes | Yes | Yes |
| **RIVAGE PM** | Yes | Yes | Yes | — | Yes | Yes |
| **DiGiCo SD** | Yes | Yes | Yes | Yes | — | Yes |
| **A&H dLive** | Yes | Yes | Yes | Yes | Yes | — |

**6 formats = 30 translation directions.** Each requires one parser + one writer = 12 modules total (6 parsers + 6 writers), not 30 separate translators. This is the power of the universal model architecture.

### High-Demand Translation Pairs (Priority for Testing)

| Pair | Why it matters |
|------|---------------|
| Yamaha CL → DiGiCo SD | The #1 most common cross-brand switch in touring |
| DiGiCo SD → Yamaha CL | Reverse of above |
| A&H dLive → DiGiCo SD | A&H engineers guesting on DiGiCo-equipped festivals |
| Yamaha CL → A&H dLive | Festival scenario — Yamaha engineers on A&H stages |
| Yamaha CL → Yamaha TF | Downgrade scenario — CL engineer arrives at venue with TF |
| Yamaha CL → Yamaha DM7 | In-brand migration — upgrading/sidegrade to DM7 |
| DiGiCo SD → A&H dLive | Cross-brand touring scenario |

---

## 8. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| MBDF container is encrypted or compressed | Low-Medium | High — blocks entire Yamaha MBDF family | Examine `#MMS FIE` sections carefully. If encrypted, investigate if Yamaha editors decrypt on load. Worst case: intercept editor's file I/O. |
| Real DiGiCo .show files are complex binary, not XML | Medium | Medium — increases DiGiCo effort by 2-3x | Start by examining the file in a hex editor before committing to a parsing approach. DiGiCo's history leans XML. |
| Consoles reject writer output due to checksums/CRC | Medium | High — writers produce files consoles won't load | Template-based approach minimizes this risk (start from valid file, modify only parameter bytes). Test on actual console ASAP. |
| Universal model needs extension for new console features | Medium | Low — straightforward to add fields | Review model before Phase 1 starts. Add optional fields for Silk processing, additional bus types, etc. |
| User cannot produce calibration files in time | Low | High — blocks all parsing work | Provide a detailed step-by-step guide. Offer to screen-share and walk through the first editor. |
| A competing product launches multi-console support | Low | Medium — erodes first-mover advantage | Speed is the answer. The parallelization strategy is designed for maximum velocity. |

---

## 9. Next Actions

### Immediate (This Week)

1. **User:** Install DM7 Editor, TF Editor, and RIVAGE PM Editor
2. **User:** Produce the standard 7-file calibration set for DM7 (highest MBDF priority)
3. **User:** Reach out to colleagues for real DiGiCo `.show` files and A&H dLive show files
4. **Agent:** Create the calibration file guide document (`docs/guides/calibration-file-guide.md`)
5. **Agent:** Review and extend the universal model if needed for MBDF/DiGiCo/A&H features

### Next (Once Calibration Files Are Ready)

6. **Agent:** Begin MBDF reverse-engineering with DM7 calibration files
7. **Agent (parallel):** Begin DiGiCo format investigation with real `.show` files
8. **Agent (parallel):** Begin A&H format investigation when files arrive

### Following (After Parsers Are Built)

9. **Agent:** Develop writers for each parsed format (template-based approach)
10. **Agent:** Wire all parsers and writers into `translator.py`
11. **Agent:** Update web UI to offer new console options
12. **User:** Test translated files on real consoles (or in offline editors as proxy)
