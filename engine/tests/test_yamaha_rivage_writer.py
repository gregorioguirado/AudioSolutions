"""Round-trip tests for the Yamaha RIVAGE PM binary writer.

Strategy: parse a calibration sample, write it via ``write_yamaha_rivage``,
then re-parse and assert that the key parameters survived intact.
"""
from __future__ import annotations

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
from parsers.yamaha_rivage import parse
from writers.yamaha_rivage import write_yamaha_rivage

SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples"
RIVAGE_SAMPLE = SAMPLES_DIR / "rivage_hpf_calib.RIVAGEPM"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reparse(output: bytes) -> ShowFile:
    """Write *output* to a temp file and re-parse it with the RIVAGE parser."""
    with tempfile.NamedTemporaryFile(suffix=".RIVAGEPM", delete=False) as f:
        tmp = Path(f.name)
        tmp.write_bytes(output)
    try:
        return parse(str(tmp))
    finally:
        tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

def test_returns_bytes() -> None:
    show = parse(str(RIVAGE_SAMPLE))
    out = write_yamaha_rivage(show)
    assert isinstance(out, bytes)
    assert len(out) > 1024


def test_output_starts_with_mbdf_magic() -> None:
    show = parse(str(RIVAGE_SAMPLE))
    out = write_yamaha_rivage(show)
    assert out.startswith(b"#YAMAHA MBDFProjectFile")


def test_template_not_mutated_across_calls() -> None:
    """Calling the writer twice must not mutate the module-level template cache."""
    show = parse(str(RIVAGE_SAMPLE))
    a = write_yamaha_rivage(show)
    b = write_yamaha_rivage(show)
    assert a == b, "writer is not deterministic — inner template was mutated"


# ---------------------------------------------------------------------------
# Round-trip: real calibration sample
# ---------------------------------------------------------------------------

def test_round_trip_channel_count() -> None:
    source = parse(str(RIVAGE_SAMPLE))
    out = write_yamaha_rivage(source)
    target = _reparse(out)
    assert len(target.channels) == len(source.channels)


def test_round_trip_channel_names() -> None:
    source = parse(str(RIVAGE_SAMPLE))
    out = write_yamaha_rivage(source)
    target = _reparse(out)

    src_names = [ch.name for ch in source.channels]
    tgt_names = [ch.name for ch in target.channels]
    assert tgt_names == src_names, (
        f"First mismatch: {next((s,t) for s,t in zip(src_names,tgt_names) if s!=t)}"
    )


def test_round_trip_channel_colors() -> None:
    source = parse(str(RIVAGE_SAMPLE))
    out = write_yamaha_rivage(source)
    target = _reparse(out)

    for src, tgt in zip(source.channels, target.channels):
        assert src.color == tgt.color, (
            f"ch{src.id}: color {src.color} != {tgt.color}"
        )


def test_round_trip_hpf() -> None:
    source = parse(str(RIVAGE_SAMPLE))
    out = write_yamaha_rivage(source)
    target = _reparse(out)

    for src, tgt in zip(source.channels, target.channels):
        assert src.hpf_enabled == tgt.hpf_enabled, (
            f"ch{src.id}: hpf_enabled {src.hpf_enabled} != {tgt.hpf_enabled}"
        )
        assert abs(src.hpf_frequency - tgt.hpf_frequency) < 1.0, (
            f"ch{src.id}: hpf_freq {src.hpf_frequency} Hz vs {tgt.hpf_frequency} Hz"
        )


# ---------------------------------------------------------------------------
# Round-trip: synthetic ShowFile (synthetic values covering all offsets)
# ---------------------------------------------------------------------------

def _make_synthetic_show() -> ShowFile:
    show = ShowFile(source_console="yamaha_rivage_pm")
    show.channels.append(Channel(
        id=1,
        name="Kick",
        color=ChannelColor.RED,
        input_patch=1,
        hpf_frequency=80.0,
        hpf_enabled=True,
        eq_bands=[
            EQBand(frequency=200.0,  gain=3.0,  q=1.5, band_type=EQBandType.PEAK, enabled=True),
            EQBand(frequency=800.0,  gain=-2.0, q=0.7, band_type=EQBandType.PEAK, enabled=True),
            EQBand(frequency=3000.0, gain=1.5,  q=0.7, band_type=EQBandType.PEAK, enabled=True),
            EQBand(frequency=8000.0, gain=-1.0, q=4.0, band_type=EQBandType.PEAK, enabled=False),
        ],
        gate=Gate(threshold=-40.0, attack=5.0, hold=10.0, release=200.0, enabled=True),
        compressor=Compressor(
            threshold=-20.0, ratio=4.0, attack=15.0,
            release=150.0, makeup_gain=0.0, enabled=True,
        ),
    ))
    show.channels.append(Channel(
        id=2,
        name="Snare",
        color=ChannelColor.BLUE,
        input_patch=2,
        hpf_frequency=120.0,
        hpf_enabled=True,
    ))
    return show


def test_synthetic_round_trip_names() -> None:
    show = _make_synthetic_show()
    out = write_yamaha_rivage(show)
    target = _reparse(out)

    assert target.channels[0].name == "Kick"
    assert target.channels[1].name == "Snare"


def test_synthetic_round_trip_hpf() -> None:
    show = _make_synthetic_show()
    out = write_yamaha_rivage(show)
    target = _reparse(out)

    assert target.channels[0].hpf_enabled is True
    assert abs(target.channels[0].hpf_frequency - 80.0) < 1.0

    assert target.channels[1].hpf_enabled is True
    assert abs(target.channels[1].hpf_frequency - 120.0) < 1.0


def test_synthetic_round_trip_eq_bands() -> None:
    show = _make_synthetic_show()
    out = write_yamaha_rivage(show)
    target = _reparse(out)

    rt_bands = target.channels[0].eq_bands
    assert len(rt_bands) == 4

    src_bands = show.channels[0].eq_bands
    for i, (src, tgt) in enumerate(zip(src_bands, rt_bands)):
        assert abs(tgt.frequency - src.frequency) < 1.0, (
            f"band {i}: freq {src.frequency} -> {tgt.frequency}"
        )
        assert abs(tgt.gain - src.gain) < 0.02, (
            f"band {i}: gain {src.gain} -> {tgt.gain}"
        )
        assert abs(tgt.q - src.q) < 0.002, (
            f"band {i}: Q {src.q} -> {tgt.q}"
        )

    # Band 4 was written with enabled=False (bypassed)
    assert rt_bands[3].enabled is False


def test_synthetic_round_trip_gate() -> None:
    show = _make_synthetic_show()
    out = write_yamaha_rivage(show)
    target = _reparse(out)

    rt_gate = target.channels[0].gate
    assert rt_gate is not None
    assert rt_gate.enabled is True
    assert abs(rt_gate.threshold - -40.0) < 0.02
    assert abs(rt_gate.attack - 5.0) < 1.0
    assert abs(rt_gate.hold - 10.0) < 1.0
    assert abs(rt_gate.release - 200.0) < 1.0


def test_synthetic_round_trip_compressor() -> None:
    show = _make_synthetic_show()
    out = write_yamaha_rivage(show)
    target = _reparse(out)

    rt_comp = target.channels[0].compressor
    assert rt_comp is not None
    assert rt_comp.enabled is True
    assert abs(rt_comp.threshold - -20.0) < 0.02
    assert abs(rt_comp.attack - 15.0) < 1.0
    assert abs(rt_comp.release - 150.0) < 1.0
    assert abs(rt_comp.ratio - 4.0) < 0.02


def test_synthetic_round_trip_color() -> None:
    show = _make_synthetic_show()
    out = write_yamaha_rivage(show)
    target = _reparse(out)

    assert target.channels[0].color == ChannelColor.RED
    assert target.channels[1].color == ChannelColor.BLUE
