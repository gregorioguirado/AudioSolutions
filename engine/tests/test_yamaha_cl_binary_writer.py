"""Tests for the template-based Yamaha CL binary writer.

The writer takes a universal ``ShowFile`` and overwrites parameter bytes
inside a copy of the empty CL5 calibration template.  Round-trip tests
parse the output back via the existing binary parser and assert that
each parameter class survives the trip.
"""
from __future__ import annotations

import struct
from pathlib import Path

import pytest

from models.universal import (
    ChannelColor,
    Compressor,
    EQBand,
    EQBandType,
    Gate,
    ShowFile,
    Channel,
)
from parsers.yamaha_cl_binary import (
    COLOR_TABLE_REL,
    CHANNEL_OFF_REL,
    FADER_REL,
    HPF_ENABLE_REL,
    HPF_FREQ_REL,
    NAME_TABLE_1_REL,
    NAME_TABLE_2_REL,
    PAN_REL,
    _find_all_memapi,
    _pick_best_scene,
    parse_yamaha_cl_binary,
)
from writers.yamaha_cl_binary import (
    DEFAULT_FADER_VALUE,
    DEFAULT_PAN_VALUE,
    write_yamaha_cl_binary,
)

SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def example1_clf() -> Path:
    return SAMPLES_DIR / "Example 1 CL5.CLF"


@pytest.fixture
def example1_show(example1_clf: Path) -> ShowFile:
    return parse_yamaha_cl_binary(example1_clf)


def _reparse(output: bytes, tmp_path: Path) -> ShowFile:
    """Write *output* to a temp .CLF and re-parse it via the binary parser."""
    target = tmp_path / "out.CLF"
    target.write_bytes(output)
    return parse_yamaha_cl_binary(target)


def _scene_offset(data: bytes) -> int:
    scenes = _find_all_memapi(data)
    return _pick_best_scene(data, scenes)


# ---------------------------------------------------------------------------
# Smoke
# ---------------------------------------------------------------------------

def test_returns_bytes(example1_show: ShowFile) -> None:
    out = write_yamaha_cl_binary(example1_show)
    assert isinstance(out, bytes)
    assert len(out) > 1024


def test_output_contains_memapi(example1_show: ShowFile) -> None:
    out = write_yamaha_cl_binary(example1_show)
    assert b"MEMAPI" in out


def test_template_not_mutated_across_calls(example1_show: ShowFile) -> None:
    """Calling the writer twice must not mutate the in-memory template."""
    a = write_yamaha_cl_binary(example1_show)
    b = write_yamaha_cl_binary(example1_show)
    assert a == b, "writer is not deterministic — template was mutated"


# ---------------------------------------------------------------------------
# Channel names (priority 1)
# ---------------------------------------------------------------------------

def test_write_cl_binary_preserves_channel_names(
    example1_show: ShowFile, tmp_path: Path
) -> None:
    """Round-trip: source channel names == re-parsed channel names."""
    out = write_yamaha_cl_binary(example1_show)
    reparsed = _reparse(out, tmp_path)

    assert len(reparsed.channels) == len(example1_show.channels)
    src_names = [ch.name for ch in example1_show.channels]
    rt_names = [ch.name for ch in reparsed.channels]
    assert rt_names == src_names


# ---------------------------------------------------------------------------
# Channel colors (priority 2)
# ---------------------------------------------------------------------------

def test_round_trip_channel_colors(tmp_path: Path) -> None:
    """Each named ChannelColor that the binary palette supports must survive."""
    show = ShowFile(source_console="yamaha_cl")
    palette = [
        ChannelColor.RED,
        ChannelColor.GREEN,
        ChannelColor.YELLOW,
        ChannelColor.BLUE,
        ChannelColor.PURPLE,
        ChannelColor.CYAN,
        ChannelColor.WHITE,
        ChannelColor.OFF,
    ]
    for i, color in enumerate(palette, start=1):
        show.channels.append(Channel(
            id=i,
            name=f"col{i}",
            color=color,
            input_patch=i,
            hpf_frequency=20.0,
            hpf_enabled=False,
        ))

    out = write_yamaha_cl_binary(show)
    reparsed = _reparse(out, tmp_path)

    for src, tgt in zip(show.channels, reparsed.channels[: len(show.channels)]):
        assert src.color == tgt.color, f"ch{src.id}: color {src.color} != {tgt.color}"


# ---------------------------------------------------------------------------
# HPF (priority 3)
# ---------------------------------------------------------------------------

def test_round_trip_hpf(tmp_path: Path) -> None:
    show = ShowFile(source_console="yamaha_cl")
    show.channels.append(Channel(
        id=1, name="kick", color=ChannelColor.RED, input_patch=1,
        hpf_frequency=80.0, hpf_enabled=True,
    ))
    show.channels.append(Channel(
        id=2, name="snare", color=ChannelColor.WHITE, input_patch=2,
        hpf_frequency=200.0, hpf_enabled=True,
    ))
    show.channels.append(Channel(
        id=3, name="bass", color=ChannelColor.BLUE, input_patch=3,
        hpf_frequency=20.0, hpf_enabled=False,
    ))

    out = write_yamaha_cl_binary(show)
    reparsed = _reparse(out, tmp_path)

    assert reparsed.channels[0].hpf_enabled is True
    assert reparsed.channels[1].hpf_enabled is True
    assert reparsed.channels[2].hpf_enabled is False

    # Frequency reconstruction has small log-quantization error; tolerate ~6%
    assert abs(reparsed.channels[0].hpf_frequency - 80.0) < 6.0
    assert abs(reparsed.channels[1].hpf_frequency - 200.0) < 12.0


# ---------------------------------------------------------------------------
# EQ (priority 4)
# ---------------------------------------------------------------------------

def test_round_trip_eq_band_frequencies(tmp_path: Path) -> None:
    """Each EQ band's frequency must round-trip within semitone tolerance."""
    show = ShowFile(source_console="yamaha_cl")
    bands = [
        EQBand(frequency=200.0, gain=3.0, q=4.0, band_type=EQBandType.PEAK),
        EQBand(frequency=800.0, gain=-2.0, q=0.7, band_type=EQBandType.PEAK),
        EQBand(frequency=3000.0, gain=1.5, q=0.7, band_type=EQBandType.PEAK),
        EQBand(frequency=8000.0, gain=-1.0, q=4.0, band_type=EQBandType.PEAK),
    ]
    show.channels.append(Channel(
        id=1, name="lead", color=ChannelColor.RED, input_patch=1,
        hpf_frequency=20.0, hpf_enabled=False, eq_bands=bands,
    ))

    out = write_yamaha_cl_binary(show)
    reparsed = _reparse(out, tmp_path)

    rt_bands = reparsed.channels[0].eq_bands
    assert len(rt_bands) == 4
    for src, tgt in zip(bands, rt_bands):
        # Semitone scale: 1 semitone ~ 6% frequency error tolerance.
        assert tgt.frequency == pytest.approx(src.frequency, rel=0.06), (
            f"freq {src.frequency} -> {tgt.frequency}"
        )


def test_round_trip_eq_band_gain(tmp_path: Path) -> None:
    show = ShowFile(source_console="yamaha_cl")
    bands = [
        EQBand(frequency=125.0, gain=4.0, q=4.0, band_type=EQBandType.PEAK),
        EQBand(frequency=1000.0, gain=-3.0, q=0.7, band_type=EQBandType.PEAK),
        EQBand(frequency=4000.0, gain=2.5, q=0.7, band_type=EQBandType.PEAK),
        EQBand(frequency=10000.0, gain=-5.0, q=4.0, band_type=EQBandType.PEAK),
    ]
    show.channels.append(Channel(
        id=1, name="vox", color=ChannelColor.GREEN, input_patch=1,
        hpf_frequency=20.0, hpf_enabled=False, eq_bands=bands,
    ))

    out = write_yamaha_cl_binary(show)
    reparsed = _reparse(out, tmp_path)

    rt_bands = reparsed.channels[0].eq_bands
    for src, tgt in zip(bands, rt_bands):
        assert abs(tgt.gain - src.gain) < 0.2, f"gain {src.gain} -> {tgt.gain}"


# ---------------------------------------------------------------------------
# Dynamics (priority 5)
# ---------------------------------------------------------------------------

def test_round_trip_gate(tmp_path: Path) -> None:
    show = ShowFile(source_console="yamaha_cl")
    gate = Gate(threshold=-30.0, attack=5.0, hold=10.0, release=200.0, enabled=True)
    show.channels.append(Channel(
        id=1, name="kik", color=ChannelColor.RED, input_patch=1,
        hpf_frequency=20.0, hpf_enabled=False, gate=gate,
    ))

    out = write_yamaha_cl_binary(show)
    reparsed = _reparse(out, tmp_path)

    rt_gate = reparsed.channels[0].gate
    assert rt_gate is not None
    assert rt_gate.enabled is True
    assert abs(rt_gate.threshold - -30.0) < 0.5
    assert rt_gate.attack == pytest.approx(5.0, abs=1.0)


def test_round_trip_compressor(tmp_path: Path) -> None:
    show = ShowFile(source_console="yamaha_cl")
    comp = Compressor(threshold=-20.0, ratio=4.0, attack=15.0,
                      release=200.0, makeup_gain=2.0, enabled=True)
    show.channels.append(Channel(
        id=1, name="bass", color=ChannelColor.BLUE, input_patch=1,
        hpf_frequency=20.0, hpf_enabled=False, compressor=comp,
    ))

    out = write_yamaha_cl_binary(show)
    reparsed = _reparse(out, tmp_path)

    rt = reparsed.channels[0].compressor
    assert rt is not None
    assert rt.enabled is True
    assert abs(rt.threshold - -20.0) < 0.5
    assert rt.attack == pytest.approx(15.0, abs=1.0)
    # Ratio is approximate (log scale, byte-quantized)
    assert rt.ratio == pytest.approx(4.0, rel=0.25)


# ---------------------------------------------------------------------------
# Fader / Pan / Mute (priority 6)
# ---------------------------------------------------------------------------

def test_round_trip_mute(tmp_path: Path) -> None:
    show = ShowFile(source_console="yamaha_cl")
    show.channels.append(Channel(
        id=1, name="on", color=ChannelColor.RED, input_patch=1,
        hpf_frequency=20.0, hpf_enabled=False, muted=False,
    ))
    show.channels.append(Channel(
        id=2, name="off", color=ChannelColor.RED, input_patch=2,
        hpf_frequency=20.0, hpf_enabled=False, muted=True,
    ))

    out = write_yamaha_cl_binary(show)
    reparsed = _reparse(out, tmp_path)

    assert reparsed.channels[0].muted is False
    assert reparsed.channels[1].muted is True


def test_writer_writes_default_fader_and_pan_bytes(tmp_path: Path) -> None:
    """The universal model has no fader/pan field; the writer must still emit
    well-formed default bytes so the output is a valid CLF.
    """
    show = ShowFile(source_console="yamaha_cl")
    show.channels.append(Channel(
        id=1, name="ch1", color=ChannelColor.RED, input_patch=1,
        hpf_frequency=20.0, hpf_enabled=False,
    ))

    out = write_yamaha_cl_binary(show)
    scene = _scene_offset(out)

    fader_bytes = out[scene + FADER_REL: scene + FADER_REL + 2]
    fader_val = struct.unpack(">H", fader_bytes)[0]
    assert fader_val == DEFAULT_FADER_VALUE

    pan_byte = out[scene + PAN_REL]
    # Signed wrap: DEFAULT_PAN_VALUE could be 0 or any signed int
    expected = DEFAULT_PAN_VALUE & 0xFF
    assert pan_byte == expected


# ---------------------------------------------------------------------------
# DCA assignments (priority 8)
# ---------------------------------------------------------------------------

def test_round_trip_dca_assignments(tmp_path: Path) -> None:
    show = ShowFile(source_console="yamaha_cl")
    show.channels.append(Channel(
        id=1, name="kick", color=ChannelColor.RED, input_patch=1,
        hpf_frequency=20.0, hpf_enabled=False,
        vca_assignments=[1, 3, 8],
    ))
    show.channels.append(Channel(
        id=2, name="snare", color=ChannelColor.WHITE, input_patch=2,
        hpf_frequency=20.0, hpf_enabled=False,
        vca_assignments=[2],
    ))

    out = write_yamaha_cl_binary(show)
    reparsed = _reparse(out, tmp_path)

    assert sorted(reparsed.channels[0].vca_assignments) == [1, 3, 8]
    assert sorted(reparsed.channels[1].vca_assignments) == [2]


# ---------------------------------------------------------------------------
# End-to-end round-trip from real CL5 file
# ---------------------------------------------------------------------------

def test_full_round_trip_real_file(example1_show: ShowFile, tmp_path: Path) -> None:
    """Round-trip the Example 1 CL5 file through the writer and back.

    Asserts the major parameter classes survive: names, colors, HPF state, mute.
    """
    out = write_yamaha_cl_binary(example1_show)
    reparsed = _reparse(out, tmp_path)

    assert len(reparsed.channels) == len(example1_show.channels)

    for src, tgt in zip(example1_show.channels, reparsed.channels):
        assert src.name == tgt.name, f"ch{src.id}: name '{src.name}' != '{tgt.name}'"
        assert src.color == tgt.color, f"ch{src.id}: color mismatch"
        assert src.hpf_enabled == tgt.hpf_enabled, f"ch{src.id}: hpf_enabled mismatch"
        assert src.muted == tgt.muted, f"ch{src.id}: muted mismatch"
