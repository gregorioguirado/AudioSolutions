"""E2E parametrized sweep via HTTP: every sample × every writable target.

Requires ``ENGINE_URL`` env var to be set (e.g. https://audiosolutions-production.up.railway.app).
If the variable is absent the entire module is skipped.

For each (file, target) pair:
  - POSTs to ``{ENGINE_URL}/translate``
  - asserts HTTP 200
  - asserts the response ZIP contains the expected output filename + translation_report.pdf
"""
from __future__ import annotations

import os
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
import requests

ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from translator import WRITERS  # noqa: E402

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"

EXT_TO_SOURCE: dict[str, str] = {
    ".clf": "yamaha_cl",
    ".cle": "yamaha_cl",
    ".dm7f": "yamaha_dm7",
    ".tff": "yamaha_tf",
    ".rivagepm": "yamaha_rivage",
    ".show": "digico_sd",
}

OUTPUT_FILENAMES: dict[str, str] = {
    "digico_sd": "translated.show",
    "yamaha_cl": "translated.cle",
    "yamaha_cl_binary": "translated.clf",
    "yamaha_ql": "translated.clf",
    "ah_dlive": "translated.AHsession",
}

WRITABLE_TARGETS = [t for t in WRITERS if t != "ah_dlive"]


def _build_params() -> list[tuple[Path, str, str]]:
    combos: list[tuple[Path, str, str]] = []
    for f in sorted(SAMPLES_DIR.iterdir()):
        if not f.is_file():
            continue
        src = EXT_TO_SOURCE.get(f.suffix.lower())
        if src is None:
            continue
        for tgt in WRITABLE_TARGETS:
            if tgt == src:
                continue
            combos.append((f, src, tgt))
    return combos


_PARAMS = _build_params()
_IDS = [f"{p.name}→{tgt}" for p, _src, tgt in _PARAMS]

# Module-level skip if ENGINE_URL not configured
ENGINE_URL = os.environ.get("ENGINE_URL", "")
if not ENGINE_URL:
    pytest.skip("ENGINE_URL not set — skipping E2E sweep", allow_module_level=True)

# Collect fidelity for summary
_e2e_fidelity: list[tuple[str, str, float | None]] = []


@pytest.mark.parametrize("sample_path,source_console,target_console", _PARAMS, ids=_IDS)
def test_translate_route_e2e(sample_path: Path, source_console: str, target_console: str) -> None:
    """POST file to engine and assert 200 + valid ZIP bundle."""
    with open(sample_path, "rb") as fh:
        resp = requests.post(
            f"{ENGINE_URL}/translate",
            data={"source_console": source_console, "target_console": target_console},
            files={"file": (sample_path.name, fh)},
            timeout=60,
        )

    assert resp.status_code == 200, (
        f"Expected 200 for {sample_path.name} → {target_console}, "
        f"got {resp.status_code}: {resp.text[:200]}"
    )

    # Verify ZIP structure
    bundle = zipfile.ZipFile(BytesIO(resp.content))
    names_in_zip = bundle.namelist()

    expected_output = OUTPUT_FILENAMES.get(target_console, "translated.bin")
    assert expected_output in names_in_zip, (
        f"Expected '{expected_output}' in ZIP for {sample_path.name} → {target_console}, "
        f"found: {names_in_zip}"
    )
    assert "translation_report.pdf" in names_in_zip, (
        f"translation_report.pdf missing from ZIP for {sample_path.name} → {target_console}"
    )

    overall_str = resp.headers.get("X-Fidelity-Overall")
    overall: float | None = float(overall_str) if overall_str else None
    _e2e_fidelity.append((sample_path.name, target_console, overall))


def test_zzz_print_e2e_fidelity_summary() -> None:
    """Always-passing test that prints the E2E fidelity table."""
    if not _e2e_fidelity:
        print("\n[no E2E fidelity results collected]")
        return
    header = f"{'File':<45} {'Target':<20} {'Overall':>8}"
    print(f"\n{'='*len(header)}")
    print(header)
    print("-" * len(header))
    for fname, tgt, score in sorted(_e2e_fidelity):
        score_str = f"{score:.2f}%" if score is not None else "N/A"
        print(f"{fname:<45} {tgt:<20} {score_str:>8}")
    print("=" * len(header))
