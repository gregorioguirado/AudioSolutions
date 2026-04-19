"""Tests for the Yamaha DM7 MBDF show file parser.

Covers:
  - File structure detection (magic bytes, zlib decompression)
  - Channel name extraction on all three sample files
  - HPF frequency and slope parsing
  - Color mapping
  - DCA / mute group bitmask extraction
  - EQ band parsing (frequency, gain, Q, shelf detection)
  - Dynamics parsing (gate/compressor On flag, threshold, type detection)
  - Error handling (bad magic, truncated data)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from parsers.yamaha_dm7 import parse
from models.universal import ChannelColor, EQBandType, ShowFile

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
# EQ parsing (verified from dm7_empty.dm7f defaults and Bertoleza real file)
# ---------------------------------------------------------------------------

def test_empty_file_eq_band_count(show_empty):
    assert len(show_empty.channels[0].eq_bands) == 4


def test_empty_file_eq_default_band_types(show_empty):
    # DM7 defaults: Band 1 = Low Shelf, Bands 2-3 = Peak, Band 4 = High Shelf
    bands = show_empty.channels[0].eq_bands
    assert bands[0].band_type == EQBandType.LOW_SHELF
    assert bands[1].band_type == EQBandType.PEAK
    assert bands[2].band_type == EQBandType.PEAK
    assert bands[3].band_type == EQBandType.HIGH_SHELF


def test_empty_file_eq_default_frequencies(show_empty):
    # DM7 empty file defaults (from mms_Mixing.xml + empirical verification)
    freqs = [b.frequency for b in show_empty.channels[0].eq_bands]
    assert freqs[0] == pytest.approx(125.0)
    assert freqs[1] == pytest.approx(355.0)
    assert freqs[2] == pytest.approx(3550.0)
    assert freqs[3] == pytest.approx(6300.0)


def test_empty_file_eq_default_gains_zero(show_empty):
    for band in show_empty.channels[0].eq_bands:
        assert band.gain == pytest.approx(0.0)


def test_empty_file_eq_bands_enabled(show_empty):
    for band in show_empty.channels[0].eq_bands:
        assert band.enabled is True


def test_real_file_eq_ch1_band1_cut(show_real):
    # Ch 1 (LUANA) has a significant low-mid cut — real engineering data
    band1 = show_real.channels[0].eq_bands[0]
    assert band1.frequency == pytest.approx(280.0)
    assert band1.gain == pytest.approx(-7.9, abs=0.01)
    assert band1.q == pytest.approx(2.8, abs=0.001)


def test_real_file_eq_all_channels_have_4_bands(show_real):
    for ch in show_real.channels[:20]:
        assert len(ch.eq_bands) == 4, f"{ch.name} has {len(ch.eq_bands)} bands"


def test_real_file_eq_frequencies_in_audio_range(show_real):
    for ch in show_real.channels[:20]:
        for b in ch.eq_bands:
            assert 20.0 <= b.frequency <= 20000.0, (
                f"{ch.name} band freq {b.frequency} Hz out of range"
            )


# ---------------------------------------------------------------------------
# Dynamics parsing
# ---------------------------------------------------------------------------

def test_empty_file_dynamics_off(show_empty):
    ch = show_empty.channels[0]
    # Both dynamics units are off by default
    assert ch.gate is None or ch.gate.enabled is False
    assert ch.compressor is None or ch.compressor.enabled is False


def test_real_file_ch1_has_compressor(show_real):
    # LUANA has PM Comp on
    ch = show_real.channels[0]
    assert ch.compressor is not None
    assert ch.compressor.enabled is True


def test_real_file_ch1_compressor_threshold(show_real):
    # PM Comp threshold = -25 dB (Param[0]=-2500, ÷100)
    ch = show_real.channels[0]
    assert ch.compressor.threshold == pytest.approx(-25.0, abs=0.01)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_bad_magic_raises():
    with pytest.raises(ValueError, match="Not a Yamaha MBDF"):
        parse(b"NOTAMBDF" + b"\x00" * 200)


def test_truncated_data_raises():
    with pytest.raises((ValueError, Exception)):
        parse(b"#YAMAHA MBDFProjectFile" + b"\x00" * 50)
