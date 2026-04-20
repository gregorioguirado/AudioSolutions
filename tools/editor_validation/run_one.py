"""Validate one translation in the real editor GUI.

Usage:
    python tools/editor_validation/run_one.py --source <file> --source-console <id> --target-console <id>

Translates the source file via engine/translator.py, writes the output to a
temporary path, and drives the target console's editor to open it. Prints
PASS/FAIL plus screenshot path on failure.
"""
from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "engine"))
sys.path.insert(0, str(REPO / "tools"))

from editor_validation.base import EditorDriver, default_output_dir, load_config  # noqa: E402
from translator import translate  # noqa: E402


OUTPUT_EXT = {
    "yamaha_cl": ".cle",
    "yamaha_cl_binary": ".CLF",
    "yamaha_ql": ".CLF",
    "yamaha_tf": ".tff",
    "yamaha_dm7": ".dm7f",
    "yamaha_rivage": ".RIVAGEPM",
    "digico_sd": ".show",
}

# Which editor handles which target console
TARGET_TO_EDITOR = {
    "yamaha_cl": "yamaha_cl",
    "yamaha_cl_binary": "yamaha_cl",
    "yamaha_ql": "yamaha_cl",
    "yamaha_tf": "yamaha_tf",
    "yamaha_dm7": "yamaha_dm7",
    "yamaha_rivage": "yamaha_rivage",
    "digico_sd": "digico_sd",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--source-console", required=True)
    parser.add_argument("--target-console", required=True)
    parser.add_argument("--config", default=str(Path(__file__).parent / "config.yaml"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    editor_name = TARGET_TO_EDITOR.get(args.target_console)
    if not editor_name:
        print(f"ERROR: no editor mapping for target_console={args.target_console!r}")
        return 2

    configs = load_config(Path(args.config))
    cfg = configs.get(editor_name)
    if not cfg:
        print(f"ERROR: editor {editor_name!r} not configured. Edit tools/editor_validation/config.yaml.")
        return 2

    print(f"Translating {args.source.name}: {args.source_console} -> {args.target_console}")
    result = translate(args.source, args.source_console, args.target_console)
    print(f"  translate OK: {result.channel_count} channels, parse_gate={result.parse_gate_passed}")
    if result.fidelity_score:
        print(f"  fidelity overall: {result.fidelity_score.overall:.1f}%")

    ext = OUTPUT_EXT.get(args.target_console, ".bin")
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(result.output_bytes)
        output_path = Path(f.name)

    print(f"Wrote translation to: {output_path}")
    print(f"Launching {editor_name} to validate...")

    driver = EditorDriver(cfg, default_output_dir())
    res = driver.validate(output_path)

    if res.status == "pass":
        print(f"[PASS] {res.editor} opened {output_path.name}")
        print(f"       {res.message}")
        return 0
    elif res.status == "skipped":
        print(f"[SKIP] {res.editor}: {res.message}")
        return 3
    elif res.status == "error":
        print(f"[ERROR] {res.editor}: {res.message}")
        if res.screenshot_path:
            print(f"        screenshot: {res.screenshot_path}")
        return 2
    else:  # fail
        print(f"[FAIL] {res.editor}: {res.message}")
        if res.screenshot_path:
            print(f"       screenshot: {res.screenshot_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
