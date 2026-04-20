"""Round-trip tests for the Yamaha DM7 binary writer.

Tests:
  1. Parse dm7_named.dm7f → write → re-parse: channel names match
  2. Channel count survives the round-trip
  3. HPF frequency and enabled flag round-trip correctly
  4. EQ band frequencies round-trip within floating-point tolerance
  5. write_yamaha_dm7 returns a bytes object that passes yamaha_dm7.parse
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the engine package root is on the path regardless of cwd.
ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from parsers.yamaha_dm7 import parse
from writers.yamaha_dm7 import write_yamaha_dm7
from models.universal import ShowFile

SAMPLES = Path(__file__).resolve().parent.parent.parent / "samples"
NAMED   = SAMPLES / "dm7_named.dm7f"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def source() -> ShowFile:
    return parse(NAMED.read_bytes())


@pytest.fixture(scope="module")
def roundtripped(source: ShowFile) -> ShowFile:
    out_bytes = write_yamaha_dm7(source)
    assert isinstance(out_bytes, bytes), "write_yamaha_dm7 must return bytes"
    return parse(out_bytes)


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_write_returns_bytes(source: ShowFile) -> None:
    result = write_yamaha_dm7(source)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_output_parseable(roundtripped: ShowFile) -> None:
    """Re-parsed output must be a valid ShowFile with channels."""
    assert isinstance(roundtripped, ShowFile)
    assert len(roundtripped.channels) > 0


def test_channel_count_preserved(source: ShowFile, roundtripped: ShowFile) -> None:
    assert len(roundtripped.channels) == len(source.channels)


# ---------------------------------------------------------------------------
# Channel names (first 8 are named in dm7_named.dm7f)
# ---------------------------------------------------------------------------

def test_first_channel_names_match(source: ShowFile, roundtripped: ShowFile) -> None:
    expected = ["KICK", "SNARE", "HH", "OH L", "OH R", "BASS DI", "GTR L", "GTR R"]
    for i, name in enumerate(expected):
        assert roundtripped.channels[i].name == name, (
            f"Ch {i+1}: expected {name!r}, got {roundtripped.channels[i].name!r}"
        )


def test_default_channel_names_preserved(source: ShowFile, roundtripped: ShowFile) -> None:
    # Channels 9–120 should still have their default DM7 names (start with 'ch')
    for ch in roundtripped.channels[8:]:
        assert ch.name.lower().startswith("ch"), (
            f"Ch {ch.id}: expected default 'ch...' name, got {ch.name!r}"
        )


# ---------------------------------------------------------------------------
# HPF
# ---------------------------------------------------------------------------

def test_hpf_frequency_round_trips(source: ShowFile, roundtripped: ShowFile) -> None:
    for src, tgt in zip(source.channels[:20], roundtripped.channels[:20]):
        assert tgt.hpf_frequency == pytest.approx(src.hpf_frequency, abs=0.1), (
            f"Ch {src.id} HPF freq: {src.hpf_frequency} → {tgt.hpf_frequency}"
        )


def test_hpf_enabled_round_trips(source: ShowFile, roundtripped: ShowFile) -> None:
    for src, tgt in zip(source.channels[:20], roundtripped.channels[:20]):
        assert tgt.hpf_enabled == src.hpf_enabled, (
            f"Ch {src.id} HPF enabled: {src.hpf_enabled} → {tgt.hpf_enabled}"
        )


# ---------------------------------------------------------------------------
# EQ
# ---------------------------------------------------------------------------

def test_eq_band_count_preserved(source: ShowFile, roundtripped: ShowFile) -> None:
    for src, tgt in zip(source.channels[:20], roundtripped.channels[:20]):
        assert len(tgt.eq_bands) == len(src.eq_bands), (
            f"Ch {src.id} EQ band count: {len(src.eq_bands)} → {len(tgt.eq_bands)}"
        )


def test_eq_frequencies_round_trip(source: ShowFile, roundtripped: ShowFile) -> None:
    for src, tgt in zip(source.channels[:10], roundtripped.channels[:10]):
        for bi, (sb, tb) in enumerate(zip(src.eq_bands, tgt.eq_bands)):
            assert tb.frequency == pytest.approx(sb.frequency, abs=0.1), (
                f"Ch {src.id} Band {bi+1} freq: {sb.frequency} → {tb.frequency}"
            )


def test_eq_gains_round_trip(source: ShowFile, roundtripped: ShowFile) -> None:
    for src, tgt in zip(source.channels[:10], roundtripped.channels[:10]):
        for bi, (sb, tb) in enumerate(zip(src.eq_bands, tgt.eq_bands)):
            assert tb.gain == pytest.approx(sb.gain, abs=0.01), (
                f"Ch {src.id} Band {bi+1} gain: {sb.gain} → {tb.gain}"
            )


# ---------------------------------------------------------------------------
# DCA assignments
# ---------------------------------------------------------------------------

def test_dca_assignments_round_trip(source: ShowFile, roundtripped: ShowFile) -> None:
    for src, tgt in zip(source.channels[:20], roundtripped.channels[:20]):
        assert sorted(tgt.vca_assignments) == sorted(src.vca_assignments), (
            f"Ch {src.id} DCA: {src.vca_assignments} → {tgt.vca_assignments}"
        )
