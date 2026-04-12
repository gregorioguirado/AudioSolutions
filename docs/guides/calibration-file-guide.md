# Calibration File Guide

How to create calibration files for reverse-engineering any mixing console's show file format.

---

## Part 1: Why We Need These Files

When a mixing console saves a show file, all the settings you've dialed in -- EQ, dynamics, fader positions, routing -- get packed into a proprietary file that only that console brand understands. To build a translator that can read those files and convert them to a different console, we need to figure out exactly where each parameter lives inside the file. The way we do this is dead simple: save a completely blank show (our baseline), then change just one thing and save again. When we compare the two files byte-by-byte, the differences jump right out and tell us exactly where that parameter is stored and how it's encoded. Do this for each group of parameters and we've got a complete map of the file format.

This method worked extremely well for the Yamaha CL5 -- we cracked 30+ parameters in a few hours using calibration files created in CL Editor. Now we need the same thing for every other console we want to support.

---

## Part 2: General Rules

Follow these every time, regardless of console brand:

1. **Always start from a blank/default show.** Launch the editor software, create a new show, and don't touch anything before saving the baseline. No templates, no "last session" recalls, no imported files. Factory defaults only.

2. **Change ONLY ONE parameter group per file.** Each calibration file isolates a specific group of settings. If you change HPF and dynamics in the same file, we can't tell which bytes belong to which parameter.

3. **Use channel 1 for all changes.** Every calibration adjustment goes on channel 1 (or input 1, depending on what the console calls it). Leave all other channels completely untouched at factory defaults.

4. **Save in the console's native format.** Use the editor software's normal "Save" or "Save As" function. If the console itself saves to USB, save from the console. If the editor software saves to a file on your computer, use that. We want the exact format the console/editor produces -- don't export, don't convert, just save.

5. **Name files consistently.** Use the naming convention in Part 6 below so we can keep everything organized across consoles.

6. **One empty baseline per console.** This is the most important file -- it's what we compare everything against.

---

## Part 3: File Analysis First

Before creating all 7 calibration files for a console, **upload just the empty baseline file first**. We analyze it before doing anything else because the full calibration set might be unnecessary -- or we might only need a fraction of it.

### Why analyze first?

- **The file might be readable as-is.** Some console formats are plain XML, JSON, or structured text. If we can read the parameters directly, calibration files are unnecessary -- we skip straight to building the parser.
- **The file might share a known format.** The Yamaha DM7, TF, and RIVAGE PM all share the `#YAMAHA MBDFProjectFile` header. DiGiCo `.show` files might be plain XML. Allen & Heath might use a database format. If we recognize the format family, we already have a head start.
- **We might only need targeted calibration files.** Even with a binary format, some parameters might be immediately identifiable while others need binary diffing. Instead of creating all 7 files upfront, we find out which ones we actually need.

### Steps

1. **Create ONLY the empty baseline file.** Launch the editor, create a blank show at factory defaults, save it in the console's native format. That's it -- don't create any calibration files yet.

2. **Drop it in `samples/` and tell the agent: "analyze this file."**

3. **Wait for the analysis results.** The agent will report:
   - File type (XML, ZIP+XML, binary, structured text, MBDF, database, etc.)
   - Whether it matches a known format family (e.g., MBDF like the other Yamaha consoles)
   - What's immediately readable vs. what needs calibration files to decode

4. **If most parameters are readable** -- we may only need 1-2 targeted calibration files to pin down any ambiguous encodings. The agent will tell you exactly which ones.

5. **If it's an unknown binary format** -- proceed with the full 7-file calibration set from Part 4.

### Why this matters

Looking at a baseline file takes 5 minutes. Creating 7 calibration files per console takes significantly longer. For 6 console families, that's the difference between a quick check and hours of methodical work in editor software -- work that might turn out to be unnecessary if the format is already human-readable. Always look first.

---

## Part 4: Parameter Sets

For each console, create these 7 files. Every change described below happens **on channel 1 only**. Everything else stays at factory defaults.

### File 1 -- Empty Baseline

No changes at all. Just create a new blank show and save it immediately.

This is the reference point for everything else.

---

### File 2 -- HPF + EQ (All Bands)

Set these on channel 1:

| Parameter | Setting |
|---|---|
| **HPF** | 200 Hz, ON |
| **EQ Band 1 (Low)** | Freq 200 Hz, Gain +3.0 dB, Q 2.0 |
| **EQ Band 2 (Low-Mid)** | Freq 800 Hz, Gain -4.0 dB, Q 1.5 (or nearest available) |
| **EQ Band 3 (High-Mid)** | Freq 3 kHz, Gain +5.0 dB, Q 0.5 |
| **EQ Band 4 (High)** | Freq 8 kHz, Gain -2.0 dB, Q 3.0 |

Notes:
- If the console has more than 4 EQ bands, set the first 4 as above and leave extras at default.
- If Q only snaps to specific values, pick the closest one and write down what you actually set.
- Make sure the HPF is switched ON, not just set to a frequency.
- Make sure EQ is ON/active (some consoles have a global EQ enable).

---

### File 3 -- Dynamics (Gate + Compressor)

Set these on channel 1:

**Gate:**

| Parameter | Setting |
|---|---|
| Gate | ON |
| Threshold | -20 dB |
| Attack | 5 ms |
| Hold | 50 ms (or nearest) |
| Decay / Release | 200 ms (or nearest) |
| Range | -40 dB |

**Compressor:**

| Parameter | Setting |
|---|---|
| Compressor | ON |
| Threshold | -15 dB |
| Ratio | 4:1 |
| Attack | 10 ms |
| Release | 100 ms (or nearest) |
| Knee | 3 (or nearest / "medium") |
| Makeup Gain | +6 dB |

Notes:
- If the console snaps hold/decay/release to preset values, just pick the closest one and note what it actually set.
- If there's no "knee" parameter or it uses soft/hard instead of a number, set it to "soft" and note it.
- If there's no "range" on the gate (some consoles call it "depth" or don't have it), skip it and note that.

---

### File 4 -- Fader, Pan, Mute, DCA

Set these on channel 1:

| Parameter | Setting |
|---|---|
| Fader | -10 dB |
| Pan | Hard Left (full L) |
| Channel ON/OFF | OFF (muted / channel off) |
| DCA assignment | Assign to DCA 1 **and** DCA 3 |

Notes:
- "Channel OFF" vs "Mute" -- use whichever the console calls its primary channel mute. If both exist, use the channel ON/OFF switch, not a mute group.
- DCA might be called VCA or DCA Group depending on the console. Assign to groups 1 and 3 (we use two to confirm the encoding pattern).

---

### File 5 -- Mix Bus Sends

Set these on channel 1:

| Parameter | Setting |
|---|---|
| Send to Mix 1 | Level -5 dB, set to PRE-fader |
| Send to Mix 3 | Level -10 dB, set to POST-fader |
| Send to Mix 5 | Level 0 dB, set to PRE-fader |

Notes:
- "Mix" might be called "Aux", "Bus", or "Mix Bus" depending on the console. Use the first set of output buses meant for monitor mixes or effects sends.
- We use three different buses at three different levels with mixed pre/post to map out the full send structure.
- If the console numbers buses differently (e.g., starting at 0 or using letters), use the 1st, 3rd, and 5th bus.

---

### File 6 -- Mute Groups + Delay

Set these on channel 1:

| Parameter | Setting |
|---|---|
| Mute Group assignment | Assign to Mute Group 1 **and** Mute Group 3 |
| Input Delay | 10 ms, ON |

Notes:
- Make sure the delay is enabled/switched ON, not just set to a time value.
- If delay is in samples or feet/meters instead of milliseconds, set it to the equivalent of 10 ms and note what unit the console uses.
- If the console doesn't have per-channel mute groups (unusual but possible), skip that part and note it.

---

### File 7 -- Preamp / Head Amp

Set these on channel 1:

| Parameter | Setting |
|---|---|
| HA / Preamp Gain | +20 dB (analog gain) |
| Digital Trim / D.Gain | +10 dB |
| 48V Phantom Power | ON |
| Phase / Polarity | INVERTED (flipped) |

Notes:
- Some editors won't let you change analog gain because it's a hardware control -- in that case, skip it and note that.
- Digital trim might be called "D.Gain", "Digital Gain", "Trim", or "Pad" depending on the console.
- If phantom power can't be set from the editor software (common -- it's usually hardware-only for safety), skip it and note that.
- Phase invert might be a button labeled with the polarity symbol or just called "Phase" or "Polarity."

---

## Part 5: Console-Specific Notes

### Yamaha CL/QL Series (DONE -- Reference Example)

| | |
|---|---|
| **Software** | CL Editor / QL Editor |
| **Download** | [Yamaha Pro Audio Downloads](https://www.yamaha.com/en/products/proaudio/cl/downloads.html) |
| **File format** | `.CLE` (editor save), `.CLF` (console USB save) |
| **Status** | Complete. All 7 calibration file sets were created and the format is fully mapped. |

This is our reference implementation. The CL Editor saves `.CLE` files, and the console saves `.CLF` files to USB. Both contain identical parameter data after their headers -- parsing one parses both.

Quirks we discovered:
- Q values are stored far away from the rest of the EQ data (thousands of bytes apart in the file)
- Gate hold and compressor release use logarithmic encoding
- Threshold values use a 2-byte stride pattern with a fixed marker byte
- EQ frequencies follow a semitone (12-steps-per-octave) scale
- HPF frequencies follow a different logarithmic scale than EQ

---

### Yamaha TF Series

| | |
|---|---|
| **Software** | TF Editor |
| **Download** | [Yamaha TF Editor Downloads](https://www.yamaha.com/en/products/proaudio/tf/downloads.html) |
| **File format** | `.tff` |
| **Notes** | Shares the `#YAMAHA MBDFProjectFile` header with DM7 and RIVAGE PM |

Key things to know:
- The TF series is Yamaha's "simplified" line, so some parameters may not exist (e.g., limited EQ band control, no independent gate range).
- The editor should let you set all basic parameters.
- We already have a real TF show file (`DOM CASMURRO 2.tff`) to cross-reference against calibration files.
- Because TF, DM7, and RIVAGE all share the same file header format, cracking one may give us significant clues about the others.

---

### Yamaha DM7

| | |
|---|---|
| **Software** | DM7 Editor |
| **Download** | [Yamaha DM7 Editor Downloads](https://www.yamaha.com/en/products/proaudio/dm7/downloads.html) |
| **File format** | `.dm7f` |
| **Notes** | Shares the `#YAMAHA MBDFProjectFile` header with TF and RIVAGE PM |

Key things to know:
- The DM7 is Yamaha's newest mid-tier console with a different architecture than CL/QL.
- It has a more modern EQ section -- may have more bands or different band types.
- DCA groups may work differently (the DM7 has "Custom Fader" layers).
- We already have a real DM7 show file (`Bertoleza Sesi Campinas.dm7f`) to cross-reference.

---

### Yamaha RIVAGE PM Series

| | |
|---|---|
| **Software** | RIVAGE PM Editor |
| **Download** | [Yamaha RIVAGE PM Editor Downloads](https://www.yamaha.com/en/products/proaudio/rivagepm/downloads.html) |
| **File format** | `.RIVAGEPM` |
| **Notes** | Shares the `#YAMAHA MBDFProjectFile` header with TF and DM7 |

Key things to know:
- The RIVAGE PM is Yamaha's flagship line (PM3, PM5, PM7, PM10) -- the most complex Yamaha console.
- It has extensive routing, multiple processing options per channel, and potentially very large files.
- The editor may require you to select a specific PM model (PM3/PM5/PM7/PM10) when creating a new show -- use PM5 as the default unless you have a reason to pick a different one.
- Channel count is much higher (up to 144 input channels on PM10), but still make all changes on channel 1.
- We already have a real RIVAGE file (`RIVAGE EMI 21.3.RIVAGEPM`) to cross-reference.

---

### DiGiCo SD / Quantum Series

| | |
|---|---|
| **Software** | SD Software (offline editor) |
| **Download** | [DiGiCo Software Downloads](https://digico.biz/software/) |
| **File format** | `.show` (typically a compressed/packaged format) |
| **Notes** | DiGiCo uses session-based architecture -- very different from Yamaha |

Key things to know:
- DiGiCo's offline editor is called "SD Software" and runs as a standalone app. You'll need to pick a console model when creating a session (SD12, SD10, SD7, SD5, Quantum 225, Quantum 338, etc.) -- **use SD12** as the default for calibration files since it's the most common.
- DiGiCo files may be XML-based or a packaged format containing multiple files. If the `.show` file is actually a ZIP or archive, save it as-is -- don't extract it.
- DiGiCo uses "channels" and "busses" but the architecture is more flexible than Yamaha -- channels can be assigned to any physical input, and bus routing is highly configurable.
- EQ on DiGiCo has different band options (dynamic EQ, etc.) -- for calibration files, use the standard 4-band parametric EQ.
- DiGiCo calls their groups "Control Groups" rather than DCA/VCA.
- The gate may be labeled "Noise Gate" or just "Gate."
- **Important:** DiGiCo sessions have "snapshots" (their version of scenes). Make sure you're editing the active snapshot or the default state, not creating a new snapshot.

---

### Allen & Heath dLive / Avantis

| | |
|---|---|
| **Software** | dLive Director (for dLive) / Avantis Offline Editor (for Avantis) |
| **Download** | [Allen & Heath Downloads](https://www.allen-heath.com/hardware#checks=downloads) |
| **File format** | `.show` (dLive), `.show` (Avantis) |
| **Notes** | A&H uses a different architecture with configurable I/O and processing blocks |

Key things to know:
- dLive Director and the Avantis offline editor are separate applications -- you need the one that matches the console you're creating files for. **Start with dLive** since it's the more widely deployed console.
- A&H show files are `.show` format but may be structured differently from DiGiCo `.show` files.
- dLive has a 4-band parametric EQ plus a separate HPF/LPF section.
- Dynamics section includes a gate/expander and a compressor/limiter -- the controls should be familiar.
- A&H calls their groups "DCA" (same as Yamaha).
- Mix buses are called "Aux" on dLive (Aux 1, Aux 2, etc.) -- use Aux 1, 3, and 5 for the send calibration.
- dLive Director may require selecting a specific surface and MixRack combination when creating a new show. Use **dLive S5000 surface + DM64 MixRack** as the default if asked.
- Avantis is simpler (fixed I/O, self-contained) -- a new blank show should be straightforward.
- **Phantom power and preamp gain** are likely hardware-only on A&H and can't be set from the editor. Skip those if the software won't let you change them, and note it.

---

## Part 6: File Naming Convention

Use this exact pattern for every calibration file:

```
{console model} empty.{ext}
{console model} calibration HPF EQ.{ext}
{console model} calibration dynamics.{ext}
{console model} calibration fader pan mute DCA.{ext}
{console model} calibration mix sends.{ext}
{console model} calibration mute delay.{ext}
{console model} calibration preamp.{ext}
```

### Examples by console:

| Console | Empty | HPF EQ | Dynamics |
|---|---|---|---|
| Yamaha CL5 | `CL5 empty.CLE` | `CL5 calibration HPF EQ.CLE` | `CL5 calibration dynamics.CLE` |
| Yamaha QL5 | `QL5 empty.CLE` | `QL5 calibration HPF EQ.CLE` | `QL5 calibration dynamics.CLE` |
| Yamaha TF5 | `TF5 empty.tff` | `TF5 calibration HPF EQ.tff` | `TF5 calibration dynamics.tff` |
| Yamaha DM7 | `DM7 empty.dm7f` | `DM7 calibration HPF EQ.dm7f` | `DM7 calibration dynamics.dm7f` |
| Yamaha RIVAGE PM5 | `PM5 empty.RIVAGEPM` | `PM5 calibration HPF EQ.RIVAGEPM` | `PM5 calibration dynamics.RIVAGEPM` |
| DiGiCo SD12 | `SD12 empty.show` | `SD12 calibration HPF EQ.show` | `SD12 calibration dynamics.show` |
| A&H dLive | `dLive empty.show` | `dLive calibration HPF EQ.show` | `dLive calibration dynamics.show` |
| A&H Avantis | `Avantis empty.show` | `Avantis calibration HPF EQ.show` | `Avantis calibration dynamics.show` |

### If a parameter isn't available

If the console doesn't support a parameter (e.g., no per-channel delay, no mute groups), skip it in that file. If an entire file would be empty because the console doesn't have any of those parameters, skip the file entirely and let us know.

### If a value had to be approximated

If you couldn't set the exact value listed (e.g., Q snaps to 1.4 instead of 1.5, or hold snaps to 46 ms instead of 50 ms), that's fine -- just make a quick note of what you actually set. We need to know the real value to decode the encoding correctly. A simple text file or message like "DM7: Q Band 2 set to 1.4 (1.5 not available), Gate hold set to 46ms" is perfect.

---

## Quick Reference Checklist

For each console, you should end up with:

- [ ] 1 empty baseline file
- [ ] 1 HPF + EQ calibration file
- [ ] 1 dynamics calibration file
- [ ] 1 fader/pan/mute/DCA calibration file
- [ ] 1 mix bus sends calibration file
- [ ] 1 mute groups + delay calibration file
- [ ] 1 preamp calibration file
- [ ] Notes on any values that had to be approximated or parameters that weren't available

That's 7 files per console. For 6 console families, that's 42 files total. It sounds like a lot, but each one only takes a minute or two once you've got the editor open -- the hard part is just being disciplined about changing only one group of parameters at a time.

Thanks for doing this -- these files are the foundation of everything we build. Every console we crack starts here.
