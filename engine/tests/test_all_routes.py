"""Parametrized sweep: every sample file × every writable target console.

Runs ``translate()`` directly (no HTTP). For each (file, target) pair:
  - asserts no exception is raised
  - asserts ``result.parse_gate_passed is True``
  - prints fidelity overall as informational output (never fails on low score)

The ah_dlive target is excluded because it is a stub writer with no reader.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make sure the engine package is importable when running pytest from any cwd.
ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from translator import translate, WRITERS  # noqa: E402

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"

# Filename extension → source console id (matches tools/test_all_routes.py)
EXT_TO_SOURCE: dict[str, str] = {
    ".clf": "yamaha_cl",
    ".cle": "yamaha_cl",
    ".dm7f": "yamaha_dm7",
    ".tff": "yamaha_tf",
    ".rivagepm": "yamaha_rivage",
    ".show": "digico_sd",
}

# Writers that have a real reader (ah_dlive writer produces unreadable stubs)
WRITABLE_TARGETS = [t for t in WRITERS if t != "ah_dlive"]


def _build_params() -> list[tuple[Path, str, str]]:
    """Return (sample_path, source_console, target_console) triples."""
    combos: list[tuple[Path, str, str]] = []
    for f in sorted(SAMPLES_DIR.iterdir()):
        if not f.is_file():
            continue
        src = EXT_TO_SOURCE.get(f.suffix.lower())
        if src is None:
            continue
        for tgt in WRITABLE_TARGETS:
            # Skip same-format re-targeting (translator raises UnsupportedConsolePair)
            if tgt == src:
                continue
            # Also skip yamaha_cl_binary / yamaha_ql pointing at yamaha_cl source
            # since those share the same source parser key and would be rejected too.
            # The translator only rejects src == tgt by key, so this is fine as-is.
            combos.append((f, src, tgt))
    return combos


_PARAMS = _build_params()
_IDS = [f"{p.name}→{tgt}" for p, _src, tgt in _PARAMS]

# Collect fidelity results across all tests for the summary table
_fidelity_results: list[tuple[str, str, float | None]] = []


@pytest.mark.parametrize("sample_path,source_console,target_console", _PARAMS, ids=_IDS)
def test_translate_route(sample_path: Path, source_console: str, target_console: str) -> None:
    """Translate sample → target and assert parse gate passed."""
    result = translate(
        source_file=sample_path,
        source_console=source_console,
        target_console=target_console,
    )
    overall: float | None = None
    if result.fidelity_score is not None:
        overall = round(result.fidelity_score.overall, 2)
    _fidelity_results.append((sample_path.name, target_console, overall))

    assert result.parse_gate_passed is True, (
        f"parse gate failed for {sample_path.name} → {target_console}"
    )


def test_zzz_print_fidelity_summary() -> None:
    """Always-passing test that prints the fidelity table after the sweep."""
    if not _fidelity_results:
        print("\n[no fidelity results collected]")
        return
    header = f"{'File':<45} {'Target':<20} {'Overall':>8}"
    print(f"\n{'='*len(header)}")
    print(header)
    print("-" * len(header))
    for fname, tgt, score in sorted(_fidelity_results):
        score_str = f"{score:.2f}%" if score is not None else "N/A"
        print(f"{fname:<45} {tgt:<20} {score_str:>8}")
    print("=" * len(header))
