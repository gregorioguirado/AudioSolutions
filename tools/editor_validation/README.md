# Editor Validation Harness

The only test that can't lie. Drives each console editor's real GUI to open a translated show file and verify it was accepted.

**Runs on your Windows laptop, on demand.** Not CI-continuous. Not per-translation. It's a version-bump gate: before a release goes out, you run this and it either passes (editors accept all outputs) or it fails (specific editor + screenshot of the error dialog).

## One-time setup

```powershell
pip install pywinauto pillow
```

Fill in the editor executable paths in `config.yaml`:

```yaml
editors:
  yamaha_dm7:
    exe: 'C:\Program Files\Yamaha\DM7 Editor\DM7Editor.exe'
    window_title_prefix: 'DM7 Editor'
  yamaha_tf:
    exe: 'C:\Program Files\Yamaha\TF Editor\TFEditor.exe'
    ...
```

(The defaults in `config.yaml` are guesses — verify with `Get-ChildItem "C:\Program Files" -Recurse -Include *.exe` if needed.)

## Usage

Validate one translation:

```powershell
python tools\editor_validation\run_one.py --source samples\Bertoleza` Sesi` Campinas.dm7f --source-console yamaha_dm7 --target-console yamaha_dm7
```

Validate all writable routes against a canonical sample:

```powershell
python tools\editor_validation\run_all.py
```

## Output

```
[PASS] yamaha_dm7 opened translated_20260421.dm7f (42 channels visible in editor)
[FAIL] yamaha_cl opened with error: "different kinds of data (-7)"
       Screenshot: .tmp/editor_validation/fail_yamaha_cl.png
```

Paste the output into the commit message or release notes. **No version ships without this passing.**

## How it works

Per editor, for each test case:
1. Launch the editor executable as a subprocess.
2. Wait for the main window to appear.
3. Send `Ctrl+O` (or click File > Open via menu).
4. Type the absolute path to the translated file.
5. Press Enter.
6. Wait up to 10 seconds for either:
   - The main window title to update to include the file name (PASS), or
   - A modal dialog to appear with error text (FAIL — capture text + screenshot).
7. Close the editor cleanly (no save).

Timing-sensitive. If an editor is slow to open or its window title convention changes, the harness may produce false failures. All failures attach a screenshot so you can visually confirm.
