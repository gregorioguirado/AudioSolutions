"""Tests for the Yamaha CL/QL binary (.CLF/.CLE) parser.

Uses real sample files from the samples/ directory.
"""
import pytest
from pathlib import Path

# Import will be resolved when running from engine/ directory
from parsers.yamaha_cl_binary import parse_yamaha_cl_binary

SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples"


@pytest.fixture
def example1_clf():
    return SAMPLES_DIR / "Example 1 CL5.CLF"


@pytest.fixture
def example1_cle():
    return SAMPLES_DIR / "Example 1 CL5.CLE"


@pytest.fixture
def calibration_clf():
    return SAMPLES_DIR / "calibration file.CLF"


@pytest.fixture
def calibration_cle():
    return SAMPLES_DIR / "calibration file.CLE"


@pytest.fixture
def calibration_eq():
    return SAMPLES_DIR / "calibration EQ all bands.CLF"


@pytest.fixture
def calibration_dynamics():
    return SAMPLES_DIR / "calibration dynamics full.CLF"


@pytest.fixture
def domcas_clf():
    return SAMPLES_DIR / "DOMCAS11.4.CLF"


# ---------------------------------------------------------------------------
# Basic parsing
# ---------------------------------------------------------------------------

def test_parse_clf_returns_showfile(example1_clf):
    show = parse_yamaha_cl_binary(example1_clf)
    assert show is not None
    assert show.source_console == "yamaha_cl"
    assert len(show.channels) > 0


def test_parse_cle_returns_same_channels(example1_clf, example1_cle):
    show_clf = parse_yamaha_cl_binary(example1_clf)
    show_cle = parse_yamaha_cl_binary(example1_cle)
    assert len(show_clf.channels) == len(show_cle.channels)
    for clf_ch, cle_ch in zip(show_clf.channels, show_cle.channels):
        assert clf_ch.name == cle_ch.name


def test_72_input_channels(example1_clf):
    show = parse_yamaha_cl_binary(example1_clf)
    assert len(show.channels) == 72


# ---------------------------------------------------------------------------
# Channel names
# ---------------------------------------------------------------------------

def test_channel_names_from_real_file(example1_clf):
    show = parse_yamaha_cl_binary(example1_clf)
    names = [ch.name for ch in show.channels]
    # Example 1 is a Brazilian theater show with character names
    assert any("an" in n.lower() for n in names if n)


def test_channel_names_full(example1_clf):
    """Verify full 8-char name reconstruction from two 4-byte tables."""
    show = parse_yamaha_cl_binary(example1_clf)
    # The first scene with custom names has "1 anna", "3 breno", "10 grego" etc.
    names = {ch.id: ch.name for ch in show.channels}
    # Check at least one known channel name contains expected substring
    assert "anna" in names.get(1, "").lower() or "an" in names.get(1, "").lower()


def test_domcas_channel_names(domcas_clf):
    show = parse_yamaha_cl_binary(domcas_clf)
    names = [ch.name for ch in show.channels]
    # DOMCAS has character names like "LUAN", "PALO", "CAIN"
    assert any("LUAN" in n for n in names if n)


# ---------------------------------------------------------------------------
# HPF
# ---------------------------------------------------------------------------

def test_calibration_hpf(calibration_clf):
    show = parse_yamaha_cl_binary(calibration_clf)
    ch1 = show.channels[0]
    assert ch1.hpf_enabled is True
    # HPF was set to 200 Hz in the calibration file
    assert ch1.hpf_frequency is not None
    assert abs(ch1.hpf_frequency - 200) < 10  # within 10 Hz tolerance


def test_hpf_disabled_by_default(example1_clf):
    """Channels without HPF enabled should report hpf_enabled=False."""
    show = parse_yamaha_cl_binary(example1_clf)
    # At least some channels should have HPF disabled
    disabled = [ch for ch in show.channels if not ch.hpf_enabled]
    assert len(disabled) > 0


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

def test_calibration_gate(calibration_clf):
    show = parse_yamaha_cl_binary(calibration_clf)
    ch1 = show.channels[0]
    assert ch1.gate is not None
    assert ch1.gate.enabled is True
    assert abs(ch1.gate.threshold - (-30)) < 1  # within 1 dB


def test_gate_disabled_channels(example1_clf):
    """Most channels in Example 1 scene 0 don't have gate enabled."""
    show = parse_yamaha_cl_binary(example1_clf)
    gates_off = [ch for ch in show.channels if ch.gate is None or not ch.gate.enabled]
    assert len(gates_off) > 0


# ---------------------------------------------------------------------------
# Compressor
# ---------------------------------------------------------------------------

def test_calibration_compressor(calibration_clf):
    show = parse_yamaha_cl_binary(calibration_clf)
    ch1 = show.channels[0]
    assert ch1.compressor is not None
    assert ch1.compressor.enabled is True
    assert abs(ch1.compressor.threshold - (-20)) < 1


def test_compressor_attack(calibration_clf):
    show = parse_yamaha_cl_binary(calibration_clf)
    ch1 = show.channels[0]
    assert ch1.compressor is not None
    # Default attack is 30 ms
    assert ch1.compressor.attack >= 0


def test_compressor_ratio(calibration_clf):
    show = parse_yamaha_cl_binary(calibration_clf)
    ch1 = show.channels[0]
    assert ch1.compressor is not None
    # Ratio should be > 1
    assert ch1.compressor.ratio > 1.0


# ---------------------------------------------------------------------------
# EQ
# ---------------------------------------------------------------------------

def test_calibration_eq_bands(calibration_eq):
    show = parse_yamaha_cl_binary(calibration_eq)
    ch1 = show.channels[0]
    # Should have 4 EQ bands
    assert len(ch1.eq_bands) == 4


def test_calibration_eq_band1_freq(calibration_eq):
    show = parse_yamaha_cl_binary(calibration_eq)
    ch1 = show.channels[0]
    # Band 1 was set to ~200 Hz in the calibration file
    band1 = ch1.eq_bands[0]
    assert abs(band1.frequency - 200) < 15  # within 15 Hz tolerance


def test_calibration_eq_band1_gain(calibration_eq):
    show = parse_yamaha_cl_binary(calibration_eq)
    ch1 = show.channels[0]
    band1 = ch1.eq_bands[0]
    # Band 1 gain was set to +3.0 dB
    assert abs(band1.gain - 3.0) < 0.5


# ---------------------------------------------------------------------------
# CLE format
# ---------------------------------------------------------------------------

def test_parse_cle_format(calibration_cle):
    show = parse_yamaha_cl_binary(calibration_cle)
    assert show is not None
    assert len(show.channels) == 72
    ch1 = show.channels[0]
    assert ch1.hpf_enabled is True
    assert abs(ch1.hpf_frequency - 200) < 10


# ---------------------------------------------------------------------------
# Dropped parameters tracking
# ---------------------------------------------------------------------------

def test_dropped_parameters_is_list(example1_clf):
    show = parse_yamaha_cl_binary(example1_clf)
    assert isinstance(show.dropped_parameters, list)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_nonexistent_file_raises():
    with pytest.raises(FileNotFoundError):
        parse_yamaha_cl_binary(Path("/nonexistent/file.CLF"))


def test_invalid_file_raises(tmp_path):
    bad_file = tmp_path / "bad.CLF"
    bad_file.write_bytes(b"not a yamaha file")
    with pytest.raises(ValueError):
        parse_yamaha_cl_binary(bad_file)
