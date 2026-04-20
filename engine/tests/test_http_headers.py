"""Regression tests for HTTP header encoding.

Catches the class of bugs where parser output flows into X-Translated /
X-Dropped headers with Unicode characters that Starlette's latin-1 header
encoder rejects (em-dash, smart quotes, etc.).

We exercise the full FastAPI request flow, not just `translate()`, because the
header encoding happens only when a Response is constructed. Covers every
sample file × every writable target.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from main import app  # noqa: E402
from translator import WRITERS  # noqa: E402

SAMPLES_DIR = ENGINE_DIR.parent / "samples"

EXT_TO_SOURCE = {
    ".clf": "yamaha_cl",
    ".cle": "yamaha_cl",
    ".dm7f": "yamaha_dm7",
    ".tff": "yamaha_tf",
    ".rivagepm": "yamaha_rivage",
    ".show": "digico_sd",
}

_client = TestClient(app)

_TARGETS = [t for t in WRITERS.keys() if t != "ah_dlive"]


def _collect_cases() -> list[tuple[Path, str, str]]:
    out: list[tuple[Path, str, str]] = []
    if not SAMPLES_DIR.is_dir():
        return out
    for f in sorted(SAMPLES_DIR.iterdir()):
        if not f.is_file():
            continue
        src = EXT_TO_SOURCE.get(f.suffix.lower())
        if src is None:
            continue
        for tgt in _TARGETS:
            if tgt == src:
                continue
            out.append((f, src, tgt))
    return out


@pytest.mark.parametrize(("sample", "source_console", "target_console"), _collect_cases())
def test_translate_http_route_returns_valid_headers(sample, source_console, target_console):
    with open(sample, "rb") as fh:
        files = {"file": (sample.name, fh, "application/octet-stream")}
        data = {"source_console": source_console, "target_console": target_console}
        res = _client.post("/translate", files=files, data=data)
    assert res.status_code == 200, (
        f"{sample.name}: {source_console} -> {target_console} "
        f"returned {res.status_code}: {res.text[:300]}"
    )
    # Every value must be latin-1 encodable (RFC 7230).
    for k, v in res.headers.items():
        try:
            v.encode("latin-1")
        except UnicodeEncodeError as e:
            pytest.fail(
                f"{sample.name}: header {k!r} contains non-latin-1 char: {e}"
            )
