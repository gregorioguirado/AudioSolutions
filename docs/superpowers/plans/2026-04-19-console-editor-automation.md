# Plan: Console Editor Desktop Automation
**Date:** 2026-04-19
**Goal:** Automate Yamaha QL Editor, Yamaha DM7 Editor, and DiGiCo Offline to generate calibration show files — eliminating manual steps so you only validate results.

---

## The Problem

Reverse-engineering a console format requires calibration files: known-good show files where you set channel 1 to "KICK", channel 2 to "SNARE", etc., then export and inspect the binary to learn which bytes map to which parameters. Right now that process is manual — open the app, click through menus, fill in 72 channel names one by one, export. This plan automates it.

---

## Approach

**Primary tool:** `pywinauto` — Python library for Windows GUI automation that uses Microsoft's UI Automation (UIA) accessibility API to find and interact with controls by name and type, without relying on pixel coordinates.

**Fallback:** `pyautogui` — screenshot-based automation for any UI elements rendered directly to GPU (OpenGL/DirectX faders, meters) that UIA can't see.

**Pattern per console:** Launch editor → New show → Fill channel names via scripted input → Export/Save → Collect output file.

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Custom OpenGL controls invisible to UIA | High (faders, meters) | Use keyboard shortcuts instead of clicking custom widgets |
| Qt framework controls not UIA-exposed | Medium | Try `backend="win32"` as fallback; use `PrintControlIdentifiers()` to audit |
| App version changes break selectors | Medium | Pin editor versions in docs; keep selectors readable |
| DM7 Editor needs Ethernet connection | High | Check if offline/demo mode exists; may need mock network |
| Modal dialogs block flow | Low | Add explicit waits + dialog handlers |

---

## Phase 0 — Setup (1 session, you do this)

**Install the tools:**
```
pip install pywinauto pyautogui pywin32
```

**Install the console editors (if not already):**
- Yamaha QL Editor — free download from Yamaha Pro Audio
- Yamaha DM7 Editor — free download from Yamaha Pro Audio
- DiGiCo Offline Editor — free download from DiGiCo support

**Run the discovery script (I write this):**
```
python tools/console_automation/discover.py --app "QL Editor"
```
This prints every UIA-accessible control in the running app so we know what we can automate. You share the output with me.

---

## Phase 1 — QL Editor Automation (Target: Task 3.3)

**What we need:** A QL show file with channels 1–72 named KICK, SNARE, HH, etc., plus one "all-defaults" file.

**Script:** `tools/console_automation/ql_calibration.py`

**Steps the script will perform:**
1. Launch QL Editor (`QLEditor.exe`)
2. Create new project (File → New or keyboard shortcut)
3. Navigate to channel strip list
4. For each of 72 channels: select → clear name → type new name
5. File → Save As → `samples/ql_calibration_named_channels.qlf`
6. Repeat with all defaults → `samples/ql_calibration_empty.qlf`

**Your job:** Run the script, open both output files in QL Editor, visually confirm channel names look right, send me a thumbs up.

**Unlocks:** Task 3.3 (QL validation) + QL parser confidence testing.

---

## Phase 2 — DM7 Editor Automation (Target: Task 5.1)

**What we need:** The 7-file DM7 calibration set (empty, named channels, HPF, EQ, gate, compressor, full).

**Script:** `tools/console_automation/dm7_calibration.py`

**Risk:** DM7 Editor may require a real console or network connection to save files. We'll check for an offline/standalone mode first. If it needs a network, we'll use a loopback/mock.

**Unlocks:** Task 5.1 → Task 5.2 (MBDF reverse-engineering) → DM7/TF/RIVAGE PM support.

---

## Phase 3 — DiGiCo Offline Automation (Target: Phase 0)

**What we need:** A DiGiCo SD12 .show file with the validation channel set.

**Script:** `tools/console_automation/digico_calibration.py`

**Note:** DiGiCo Offline uses Qt. UIA coverage of Qt apps is inconsistent — we may need to combine keyboard navigation with screen-region detection for custom widgets.

**Unlocks:** Phase 0 (DiGiCo validation), which unlocks the Paddle payment gate in the business model.

---

## Implementation Order

```
Phase 0 (setup + discovery)
  └─ Phase 1 (QL Editor)       ← highest value, simplest target
       └─ Phase 2 (DM7 Editor) ← MBDF batch unlocks 3 console families
            └─ Phase 3 (DiGiCo Offline) ← validates translation accuracy
```

---

## File Structure

```
tools/
  console_automation/
    __init__.py
    discover.py          # Prints all UIA controls for any running app
    ql_calibration.py    # Generates QL calibration files
    dm7_calibration.py   # Generates DM7 calibration files
    digico_calibration.py # Generates DiGiCo calibration files
    common.py            # Shared: channel name list, wait helpers, file checks
```

---

## Dependencies to Add

**`engine/requirements.txt`** (or a separate `tools/requirements.txt`):
```
pywinauto==0.6.9
pyautogui==0.9.54
pywin32==311
```

These are automation-only tools — not needed in the production engine, so a separate `tools/requirements.txt` keeps the engine image lean.

---

## Success Criteria

- Script runs end-to-end without human interaction
- Output files open correctly in the target editor
- Channel names in output match the input list exactly
- You spend < 5 minutes validating instead of 30+ minutes entering data
- Files land in `engine/samples/` ready for parser calibration

---

## Open Questions (need your answers before Phase 0)

1. Do you have QL Editor, DM7 Editor, and DiGiCo Offline already installed? If yes, where (default install path or custom)?
2. For DM7 Editor — does it open without a console connected, or does it require network/hardware?
3. Are you comfortable running `pip install pywinauto` in the engine environment, or do you want a separate venv for automation tools?
