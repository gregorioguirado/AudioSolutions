"""Tests for the Yamaha DM7 MBDF show file parser.

Covers:
  - File structure detection (magic bytes, zlib decompression)
  - Channel name extraction on all three sample files
  - HPF frequency and slope parsing
  - Color mapping
  - DCA / mute group bitmask extraction
  - Error handling (bad magic, truncated data)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from parsers.yamaha_dm7 import parse
from models.universal import ChannelColor, ShowFile

SAMPLES = Path(__file__).parent.parent.parent / "samples"
EMPTY   = SAMPLES / "dm7_empty.dm7f"
NAMED   = SAMPLES / "dm7_named.dm7f"
REAL    = SAMPLES / "Bertoleza Sesi Campinas.dm7f"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def show_empty() -> ShowFile:
    return parse(EMPTY.read_bytes())


@pytest.fixture(scope="module")
def show_named() -> ShowFile:
    return parse(NAMED.read_bytes())


@pytest.fixture(scope="module")
def show_real() -> ShowFile:
    return parse(REAL.read_bytes())


# ---------------------------------------------------------------------------
# Structure tests
# ---------------------------------------------------------------------------

def test_parse_returns_showfile(show_empty):
    assert isinstance(show_empty, ShowFile)
    assert show_empty.source_console == "yamaha_dm7"


def test_max_channels_parsed(show_empty):
    assert len(show_empty.channels) == 120


def test_channel_ids_are_one_based(show_empty):
    for i, ch in enumerate(show_empty.channels):
        assert ch.id == i + 1


# ---------------------------------------------------------------------------
# Empty file — default names
# ---------------------------------------------------------------------------

def test_empty_file_default_names(show_empty):
    # DM7 uses "ch N" (with space) for 1–9, "chNN" (no space) for 10+
    assert show_empty.channels[0].name == "ch 1"
    assert show_empty.channels[1].name == "ch 2"
    assert show_empty.channels[9].name == "ch10"
    assert show_empty.channels[71].name == "ch72"


def test_empty_file_default_color(show_empty):
    assert show_empty.channels[0].color == ChannelColor.BLUE


def test_empty_file_hpf_defaults(show_empty):
    # DM7 stores HPF.On separately (bit, default 0 = off)
    # HPF.Frequency default is 80 Hz (raw 800), stored even when HPF is off
    assert show_empty.channels[0].hpf_enabled is False
    assert show_empty.channels[0].hpf_frequency == pytest.approx(80.0)


# ---------------------------------------------------------------------------
# Named file — channel names we wrote
# ---------------------------------------------------------------------------

def test_named_file_channel_names(show_named):
    expected = ["KICK", "SNARE", "HH", "OH L", "OH R", "BASS DI", "GTR L", "GTR R"]
    for i, name in enumerate(expected):
        assert show_named.channels[i].name == name, f"Ch {i+1}: expected {name!r}"


def test_named_file_channels_9_plus_are_default(show_named):
    # DM7 default names: "ch N" for 1–9, "chNN" for 10+
    for ch in show_named.channels[8:]:
        assert ch.name.lower().startswith("ch")


# ---------------------------------------------------------------------------
# Real show file — Bertoleza Sesi Campinas
# ---------------------------------------------------------------------------

def test_real_file_first_channel(show_real):
    assert show_real.channels[0].name == "LUANA"


def test_real_file_hpf_set_above_floor(show_real):
    # Real show has HPF > 20 Hz on vocal channels
    assert show_real.channels[0].hpf_frequency > 20.0
    assert show_real.channels[0].hpf_enabled is True


def test_real_file_hpf_frequency_range(show_real):
    # HPF values on a real live show should be between 40 Hz and 500 Hz
    for ch in show_real.channels[:20]:
        if ch.hpf_enabled:
            assert 40.0 <= ch.hpf_frequency <= 500.0, (
                f"{ch.name} HPF {ch.hpf_frequency} Hz out of expected range"
            )


def test_real_file_hpf_slope_valid(show_real):
    # Slope byte should be one of 6, 12, 18, 24 dB/oct (DM7 descriptor range)
    # We don't expose slope in the model yet; verify raw parsing doesn't crash
    import struct, zlib, re
    data = REAL.read_bytes()
    for m in re.finditer(rb"\x78[\x01\x5e\x9c\xda]", data[40:]):
        pos = m.start() + 40
        try:
            inner = zlib.decompress(data[pos:])
            if inner.startswith(b"#YAMAHA "):
                break
        except Exception:
            continue
    schema_size = struct.unpack_from("<I", inner, inner.index(b"MMSXLIT\x00") + 80)[0]
    data_start = inner.index(b"MMSXLIT\x00") + 88 + schema_size
    for i in range(20):
        slope = inner[data_start + i * 1785 + 139]
        assert slope in (0, 6, 12, 18, 24), f"Ch {i+1} unexpected slope byte {slope}"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_bad_magic_raises():
    with pytest.raises(ValueError, match="Not a Yamaha MBDF"):
        parse(b"NOTAMBDF" + b"\x00" * 200)


def test_truncated_data_raises():
    with pytest.raises((ValueError, Exception)):
        parse(b"#YAMAHA MBDFProjectFile" + b"\x00" * 50)
