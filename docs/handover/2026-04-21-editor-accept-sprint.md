# Editor-accept sprint — 2026-04-21

You said: *"this is the third time I'm telling you… every editor says something like 'couldn't access file'… nothing is working for the end user."* And you asked for a verification method that **GUARANTEES** editors open the files, not a guess.

This note is what I did while you slept, and what you do when you wake up. No more "I believe it works."

## The forensic finding

Two DM7-Editor-produced empty shows (`samples/dm7_empty.dm7f` and `samples/dm7_empty2.dm7f`, saved seconds apart with identical content) differ in **one fully-random 16-byte field at file offset 0x38**. The same offset in the TF and RIVAGE templates holds the same 16-byte high-entropy pattern. CL binary has different structured data there — different problem, addressed separately.

This 16-byte field is almost certainly a **per-save session UUID**. Our writers have always copied the template's UUID into every output, so every file we've ever produced carried the same UUID as the template. The editors very likely validate this (either as a duplicate-session guard or as a key into some internal state) and reject files where it's stale.

## What shipped (v0.3.10)

- `engine/writers/yamaha_dm7.py`, `yamaha_tf.py`, `yamaha_rivage.py`: now regenerate `uuid.uuid4().bytes` at offset 0x38 on every call.
- `tools/editor_save_diff.py`: forensic byte-diff tool. Reusable for CL binary + DiGiCo once you give us duplicate editor saves of those formats.
- Tests updated to require the UUID be (a) non-zero, (b) different from template, (c) different between two consecutive writer calls.
- `CLAUDE.md` guardrail 6: I am forbidden from claiming editor compatibility without empirical proof. Stated guesses have been wrong three times. That's now in writing.
- `tools/editor_validation/`: pywinauto harness (scaffold) — see below.

## What YOU do first thing in the morning

**Step 1 — Sanity check the UUID fix.**

Run the engine, produce a DM7 output, open it in DM7 Editor. 30 seconds.

```powershell
cd "c:\Users\grego\Documents\Jobing\Claude Code\AudioSolutions"
python -c "import sys; sys.path.insert(0,'engine'); from translator import translate; from pathlib import Path; r = translate(Path('samples/Bertoleza Sesi Campinas.dm7f'), 'yamaha_dm7', 'yamaha_dm7'); Path('.tmp/test_dm7.dm7f').write_bytes(r.output_bytes); print(f'wrote {len(r.output_bytes)} bytes to .tmp/test_dm7.dm7f')"
```

Then: open `.tmp/test_dm7.dm7f` in DM7 Editor. **One of two things will happen:**

- **Editor loads the show** → UUID hypothesis was correct. Then do the same test for TF and RIVAGE (change `yamaha_dm7` → `yamaha_tf` → `yamaha_rivage` in the commands above, adjust file extensions `.tff`/`.RIVAGEPM`). If those also load, we've solved the Yamaha MBDF family. CL binary still open; see below.

- **Editor still rejects** → the UUID was not sufficient. That's information — we know there's a second volatile field or a content checksum somewhere else. Send me the exact error text and I'll dig in from there.

**Step 2 — If Step 1 passed, stand up the automation harness.**

```powershell
pip install pywinauto pillow pyyaml
```

Edit `tools\editor_validation\config.yaml` — fill in the real paths to each editor's .exe (my defaults are guesses). To find them fast:

```powershell
Get-ChildItem -Path "C:\Program Files","C:\Program Files (x86)" -Recurse -Include *.exe -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'DM7|TF|RIVAGE|Console|DiGiCo|Offline' }
```

Then run one validation end-to-end:

```powershell
python tools\editor_validation\run_one.py --source "samples\Bertoleza Sesi Campinas.dm7f" --source-console yamaha_dm7 --target-console yamaha_dm7 --verbose
```

It will launch DM7 Editor, press Ctrl+O, type the file path, and watch what happens. If the window title picks up the file name, PASS. If a modal dialog appears, FAIL with the exact dialog text + a screenshot.

If it times out or misbehaves (editor window titles don't work the way I guessed), tell me the actual window title you see and I'll adjust `base.py`.

**Step 3 — Ship v0.3.11 with the harness once it's proving things.**

Once `run_one.py` reliably PASSES for at least one editor, we have a mechanism to detect the other editors' format rejections without you manually clicking. Every version bump from here runs through the harness first.

## What's NOT fixed yet

- **CL binary** — the 16 bytes at 0x38 are structured data, not a UUID. User's error on CL5 was `"different kinds of data! (-7)"` — different class of rejection. Needs its own forensic pair: please save an empty show from Console Editor to a fresh `.CLF`, call it `samples/cl5_empty2.CLF`. I'll diff against the existing `engine/writers/templates/cl5_empty.CLF` to find the CL-specific volatile field(s).

- **DiGiCo** — same situation; please produce a second empty `.show` from DiGiCo Offline Software alongside whatever calibration files you already saved.

## What I need from you (summary)

1. **Test Step 1 (DM7/TF/RIVAGE open in editor)** and report result.
2. **If installed editors differ from the paths in `config.yaml`**, fix them.
3. **Send the actual "Open" behavior / window title** of each editor if `run_one.py` fails for reasons other than format rejection.
4. **Produce duplicate empty saves for CL and DiGiCo** so we can forensic-diff those formats next.

## What I promise

No more "I believe it works" messages. From now on every time I touch a writer, the ritual is:

1. Run `tools/editor_validation/run_one.py` against the affected target.
2. Paste the output (PASS/FAIL/SKIPPED) into the commit message.
3. If I can't run it (e.g. I'm mid-Claude-session without editor access), I explicitly say "this is unvalidated; please run `run_one.py` before merging."

Guardrail 6 in CLAUDE.md enforces this.
