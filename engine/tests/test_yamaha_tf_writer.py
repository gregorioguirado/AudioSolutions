"""Round-trip tests for the Yamaha TF binary writer.

Strategy: parse a real .tff sample → write → re-parse → assert fields survive.
The writer uses a template-patching approach (same MBDF zlib container as
RIVAGE/DM7), so a successful re-parse proves the outer container is intact.
"""
from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pytest

from models.universal import (
    Channel,
    ChannelColor,
    Compressor,
    EQBand,
    EQBandType,
    Gate,
    ShowFile,
)
from parsers.yamaha_tf import parse
from writers.yamaha_tf import write_yamaha_tf

SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples"
SAMPLE_TFF = SAMPLES_DIR / "DOM CASMURRO 2.tff"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reparse(output: bytes) -> ShowFile:
    """Write *output* to a temp .tff and re-parse it via the TF parser."""
    with tempfile.NamedTemporaryFile(suffix=".tff", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp_path.write_bytes(output)
    try:
        return parse(str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

def test_write_returns_bytes() -> None:
    source = parse(str(SAMPLE_TFF))
    out = write_yamaha_tf(source)
    assert isinstance(out, bytes)
    assert len(out) > 1024


def test_output_starts_with_yamaha_magic() -> None:
    source = parse(str(SAMPLE_TFF))
    out = write_yamaha_tf(source)
    assert out.startswith(b"#YAMAHA ")


def test_template_not_mutated_across_calls() -> None:
    """Two consecutive calls must return identical bytes (no template mutation)."""
    source = parse(str(SAMPLE_TFF))
    a = write_yamaha_tf(source)
    b = write_yamaha_tf(source)
    assert a == b, "writer is not deterministic — template was mutated"


# ---------------------------------------------------------------------------
# Primary round-trip: real TFF sample → write → re-parse
# ---------------------------------------------------------------------------

def test_round_trip_channel_1_name() -> None:
    """Channel 1 name must survive the write → re-parse cycle."""
    source = parse(str(SAMPLE_TFF))
    out = write_yamaha_tf(source)
    target = _reparse(out)

    assert target.channels[0].name == source.channels[0].name


def test_round_trip_channel_count() -> None:
    """Re-parsed file must have the same number of channels as the source."""
    source = parse(str(SAMPLE_TFF))
    out = write_yamaha_tf(source)
    target = _reparse(out)

    assert len(target.channels) == len(source.channels)


def test_round_trip_all_channel_names() -> None:
    """All channel names must survive the round-trip."""
    source = parse(str(SAMPLE_TFF))
    out = write_yamaha_tf(source)
    target = _reparse(out)

    src_names = [ch.name for ch in source.channels]
    tgt_names = [ch.name for ch in target.channels]
    assert tgt_names == src_names


# ---------------------------------------------------------------------------
# Channel colors
# ---------------------------------------------------------------------------

def test_round_trip_colors() -> None:
    """All standard ChannelColor values must survive a round-trip."""
    show = ShowFile(source_console="yamaha_tf")
    palette = [
        ChannelColor.RED,
        ChannelColor.GREEN,
        ChannelColor.YELLOW,
        ChannelColor.BLUE,
        ChannelColor.PURPLE,
        ChannelColor.CYAN,
        ChannelColor.WHITE,
    ]
    for i, color in enumerate(palette, start=1):
        show.channels.append(Channel(
            id=i, name=f"ch{i}", color=color, input_patch=None,
            hpf_frequency=100.0, hpf_enabled=False,
        ))

    out = write_yamaha_tf(show)
    target = _reparse(out)

    for src, tgt in zip(show.channels, target.channels[: len(show.channels)]):
        assert src.color == tgt.color, f"ch{src.id}: {src.color} != {tgt.color}"


# ---------------------------------------------------------------------------
# HPF
# ---------------------------------------------------------------------------

def test_round_trip_hpf_enabled() -> None:
    show = ShowFile(source_console="yamaha_tf")
    show.channels.append(Channel(
        id=1, name="kick", color=ChannelColor.RED, input_patch=None,
        hpf_frequency=80.0, hpf_enabled=True,
    ))
    show.channels.append(Channel(
        id=2, name="bass", color=ChannelColor.BLUE, input_patch=None,
        hpf_frequency=20.0, hpf_enabled=False,
    ))

    out = write_yamaha_tf(show)
    target = _reparse(out)

    assert target.channels[0].hpf_enabled is True
    assert target.channels[1].hpf_enabled is False


def test_round_trip_hpf_frequency() -> None:
    """HPF frequency must round-trip with < 1 Hz tolerance (stored as ÷10 int)."""
    show = ShowFile(source_console="yamaha_tf")
    show.channels.append(Channel(
        id=1, name="snare", color=ChannelColor.WHITE, input_patch=None,
        hpf_frequency=120.0, hpf_enabled=True,
    ))

    out = write_yamaha_tf(show)
    target = _reparse(out)

    assert abs(target.channels[0].hpf_frequency - 120.0) < 0.2


# ---------------------------------------------------------------------------
# EQ bands
# ---------------------------------------------------------------------------

def test_round_trip_eq_frequency() -> None:
    show = ShowFile(source_console="yamaha_tf")
    bands = [
        EQBand(frequency=200.0, gain=3.0, q=1.0, band_type=EQBandType.PEAK),
        EQBand(frequency=800.0, gain=-2.0, q=0.7, band_type=EQBandType.PEAK),
        EQBand(frequency=3000.0, gain=1.5, q=0.7, band_type=EQBandType.PEAK),
        EQBand(frequency=8000.0, gain=-1.0, q=2.0, band_type=EQBandType.PEAK),
    ]
    show.channels.append(Channel(
        id=1, name="vox", color=ChannelColor.GREEN, input_patch=None,
        hpf_frequency=80.0, hpf_enabled=True, eq_bands=bands,
    ))

    out = write_yamaha_tf(show)
    target = _reparse(out)

    rt_bands = target.channels[0].eq_bands
    assert len(rt_bands) == 4
    for src, tgt in zip(bands, rt_bands):
        # Stored as uint32 × 10, so precision is 0.1 Hz
        assert abs(tgt.frequency - src.frequency) < 0.2, (
            f"freq {src.frequency} -> {tgt.frequency}"
        )


def test_round_trip_eq_gain() -> None:
    show = ShowFile(source_console="yamaha_tf")
    bands = [
        EQBand(frequency=125.0, gain=4.0, q=1.0, band_type=EQBandType.PEAK),
        EQBand(frequency=1000.0, gain=-3.0, q=0.7, band_type=EQBandType.PEAK),
        EQBand(frequency=4000.0, gain=2.5, q=0.7, band_type=EQBandType.PEAK),
        EQBand(frequency=10000.0, gain=-5.0, q=2.0, band_type=EQBandType.PEAK),
    ]
    show.channels.append(Channel(
        id=1, name="gtr", color=ChannelColor.YELLOW, input_patch=None,
        hpf_frequency=80.0, hpf_enabled=True, eq_bands=bands,
    ))

    out = write_yamaha_tf(show)
    target = _reparse(out)

    rt_bands = target.channels[0].eq_bands
    for src, tgt in zip(bands, rt_bands):
        # Stored as int16 × 100, so precision is 0.01 dB
        assert abs(tgt.gain - src.gain) < 0.02, f"gain {src.gain} -> {tgt.gain}"


# ---------------------------------------------------------------------------
# Gate dynamics
# ---------------------------------------------------------------------------

def test_round_trip_gate() -> None:
    show = ShowFile(source_console="yamaha_tf")
    gate = Gate(threshold=-35.0, attack=10.0, hold=50.0, release=300.0, enabled=True)
    show.channels.append(Channel(
        id=1, name="kick", color=ChannelColor.RED, input_patch=None,
        hpf_frequency=20.0, hpf_enabled=False, gate=gate,
    ))

    out = write_yamaha_tf(show)
    target = _reparse(out)

    rt = target.channels[0].gate
    assert rt is not None
    assert rt.enabled is True
    assert abs(rt.threshold - -35.0) < 0.02   # int16 ÷100 precision
    assert rt.attack == pytest.approx(10.0, abs=1.0)
    assert abs(rt.release - 300.0) < 1.0      # uint32 µs ÷1000 precision


# ---------------------------------------------------------------------------
# Compressor dynamics
# ---------------------------------------------------------------------------

def test_round_trip_compressor() -> None:
    show = ShowFile(source_console="yamaha_tf")
    comp = Compressor(
        threshold=-20.0, ratio=4.0, attack=15.0,
        release=250.0, makeup_gain=3.0, enabled=True,
    )
    show.channels.append(Channel(
        id=1, name="bass", color=ChannelColor.BLUE, input_patch=None,
        hpf_frequency=20.0, hpf_enabled=False, compressor=comp,
    ))

    out = write_yamaha_tf(show)
    target = _reparse(out)

    rt = target.channels[0].compressor
    assert rt is not None
    assert rt.enabled is True
    assert abs(rt.threshold - -20.0) < 0.02    # int16 ÷100
    assert rt.attack == pytest.approx(15.0, abs=1.0)
    assert abs(rt.release - 250.0) < 1.0       # uint32 µs ÷1000
    assert rt.ratio == pytest.approx(4.0, rel=0.05)   # uint8 ÷10
    assert abs(rt.makeup_gain - 3.0) < 0.02    # int16 ÷100


# ---------------------------------------------------------------------------
# Full round-trip from real sample (fidelity check)
# ---------------------------------------------------------------------------

def test_full_round_trip_real_file() -> None:
    """End-to-end: DOM CASMURRO 2.tff → write → re-parse.

    Asserts names, colors, HPF state survive for all channels.
    """
    source = parse(str(SAMPLE_TFF))
    out = write_yamaha_tf(source)
    target = _reparse(out)

    assert len(target.channels) == len(source.channels)

    for src, tgt in zip(source.channels, target.channels):
        assert src.name == tgt.name, f"ch{src.id}: name '{src.name}' != '{tgt.name}'"
        assert src.color == tgt.color, f"ch{src.id}: color mismatch"
        assert src.hpf_enabled == tgt.hpf_enabled, f"ch{src.id}: hpf_enabled mismatch"
