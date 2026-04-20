# Launch Checklist — Pre-Paddle Hardening

Things that were intentionally deferred during dev/test and MUST ship before payments go live.

## Fidelity gate
- [ ] Flip the 80% fidelity hard-block in `engine/main.py` — after the existing parse-gate check, add:
  ```python
  if result.fidelity_score and result.fidelity_score.overall < 80.0:
      raise HTTPException(422, detail=f"Fidelity {result.fidelity_score.overall:.1f}% < 80% threshold")
  ```
- [ ] Frontend: convert the "low-fidelity warning banner" in `TranslationPreview.tsx` into a blocking state (download button disabled below 80%).

## yamaha_cl_binary writer fidelity leak
Today non-CL → CL binary routes score ~60%. To get them above 80%:
- [ ] Map the missing EQ Q offsets for bands 3–4 in `engine/parsers/yamaha_cl_binary.py` (currently hardcoded via `DEFAULT_Q`).
- [ ] Fix the gate release decay encoding (parser uses a log scale that doesn't round-trip through the writer).
- [ ] Handle channel count >72 — CL template has 72 input slots; DM7/TF/RIVAGE can have 120–144. Either (a) drop overflow with a clear warning, or (b) write overflow to unused template slots.

## DiGiCo real-file validation (council mandate)
- [ ] Load a translated `.show` file in DiGiCo Offline Software. Confirm it opens without errors.
- [ ] If errors, debug `engine/writers/digico_sd.py` XML structure.

## A&H dLive writer
- [ ] Replace `engine/writers/ah_dlive.py` `NotImplementedError` stub once a real `.AHsession` sample is available.

## RIVAGE makeup_gain calibration (15-min job)
- [ ] Open RIVAGE PM Editor, set OutGain +3.0 dB on CH2, save as `samples/rivage_makeup_calib.RIVAGEPM`.
- [ ] Run `tools/rivage_offset_probe.py` to locate the byte offset.
- [ ] Add the offset to `engine/parsers/yamaha_rivage.py`; update the matching fixture YAML.

## L5 Verify Before Doors acknowledgement
- [ ] Already implemented in `VerifyBeforeDoorsModal.tsx` — just confirm it still works after the fidelity block lands.
