"""Tests for engine.verification.

Includes the round-trip test mandated by the council-shifts execution plan
(`test_harness_round_trip_cl_digico_cl_preserves_channel_names`) plus
coverage for the per-parameter diff and the fixture-golden pattern.

Conventions follow the existing test_yamaha_cl_binary.py — flat imports
(no `engine.` prefix) and ``SAMPLES_DIR`` resolved relative to ``__file__``.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import pytest

from parsers.digico_sd import parse_digico_sd
from parsers.yamaha_cl_binary import parse_yamaha_cl_binary
from verification.harness import (
    HarnessResult,
    ParameterCheck,
    verify_against_fixture,
    verify_translation,
)
from verification.round_trip import RoundTripResult, round_trip
from writers.digico_sd import write_digico_sd

SAMPLES_DIR = Path(__file__).parent.parent.parent.parent / "samples"


@pytest.fixture
def example1_clf() -> Path:
    return SAMPLES_DIR / "Example 1 CL5.CLF"


@pytest.fixture
def empty_calibration_clf() -> Path:
    return SAMPLES_DIR / "empty calibration file.CLF"


# --------------------------------------------------------------------------- #
# Mandated test from the plan
# --------------------------------------------------------------------------- #


def test_harness_round_trip_cl_digico_cl_preserves_channel_names(example1_clf: Path) -> None:
    """CL5 -> DiGiCo XML -> re-parse: channel names must survive the trip.

    NOTE: the DiGiCo writer is currently SYNTHETIC and unvalidated against
    real DiGiCo Offline Software. This test asserts only the round-trip
    self-consistency of our writer/parser pair — not that the file would
    actually load on a DiGiCo console. If/when validation against real
    DiGiCo software fails, the writer (not this test) is the regression
    site.
    """

    show_a = parse_yamaha_cl_binary(example1_clf)
    xml_bytes = write_digico_sd(show_a)

    with tempfile.NamedTemporaryFile(suffix=".show", delete=False) as tmp:
        tmp.write(xml_bytes)
        tmp_path = Path(tmp.name)

    try:
        show_b = parse_digico_sd(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    assert len(show_a.channels) == len(show_b.channels), (
        f"channel count changed during round-trip: "
        f"{len(show_a.channels)} -> {len(show_b.channels)}"
    )

    mismatches = [
        (a.id, a.name, b.name)
        for a, b in zip(show_a.channels, show_b.channels)
        if a.name != b.name
    ]
    assert not mismatches, (
        "channel names changed during CL -> DiGiCo -> DiGiCo round-trip: "
        f"{mismatches[:5]} (showing up to 5 of {len(mismatches)})"
    )


# --------------------------------------------------------------------------- #
# verify_translation — direct API
# --------------------------------------------------------------------------- #


def test_verify_translation_returns_harness_result(example1_clf: Path) -> None:
    show = parse_yamaha_cl_binary(example1_clf)
    output = write_digico_sd(show)
    result = verify_translation(show, output, "digico_sd")
    assert isinstance(result, HarnessResult)
    assert result.target_format == "digico_sd"
    assert result.checks, "expected at least one parameter check"


def test_verify_translation_passes_for_clean_round_trip(example1_clf: Path) -> None:
    show = parse_yamaha_cl_binary(example1_clf)
    output = write_digico_sd(show)
    result = verify_translation(show, output, "digico_sd")
    failed = [
        c for c in result.failed_checks
        # mute_state drop is a known DiGiCo limitation, surfaced explicitly
        if not (c.parameter == "muted" and "DiGiCo" in c.note)
    ]
    assert not failed, (
        "unexpected verification failures: "
        f"{[(c.channel_id, c.parameter, c.source_value, c.target_value) for c in failed[:5]]}"
    )


def test_verify_translation_never_raises_on_garbage_bytes(example1_clf: Path) -> None:
    """The hook into translator.translate() must NEVER raise."""
    show = parse_yamaha_cl_binary(example1_clf)
    result = verify_translation(show, b"not valid xml at all", "digico_sd")
    assert isinstance(result, HarnessResult)
    assert result.fatal_error is not None
    assert not result.all_passed


def test_verify_translation_unknown_target_format_does_not_raise(example1_clf: Path) -> None:
    show = parse_yamaha_cl_binary(example1_clf)
    result = verify_translation(show, b"<x/>", "totally_made_up_console")
    assert result.fatal_error is not None


def test_failed_check_recorded_when_target_value_differs() -> None:
    # Construct an obviously-wrong "target" by swapping channel names.
    from models.universal import Channel, ChannelColor, ShowFile

    src = ShowFile(source_console="yamaha_cl", channels=[
        Channel(
            id=1, name="Kick", color=ChannelColor.RED,
            input_patch=1, hpf_frequency=80.0, hpf_enabled=True,
        ),
    ])
    output = write_digico_sd(src)

    # Tamper with the bytes: replace "Kick" with "Snare" so the re-parse
    # will return a different name.
    tampered = output.replace(b"<Name>Kick</Name>", b"<Name>Snare</Name>")
    assert tampered != output, "tampering precondition failed"

    result = verify_translation(src, tampered, "digico_sd")
    name_checks = [c for c in result.checks if c.parameter == "name"]
    assert any(not c.passed for c in name_checks), (
        "expected at least one name check to fail after tampering"
    )


# --------------------------------------------------------------------------- #
# round_trip — high-level helper
# --------------------------------------------------------------------------- #


def test_round_trip_returns_diff_report(example1_clf: Path) -> None:
    result = round_trip(example1_clf, "digico_sd")
    assert isinstance(result, RoundTripResult)
    assert result.error is None, f"unexpected error: {result.error}"
    assert result.source_show is not None
    assert result.intermediate_show is not None
    assert result.diff_report, "diff_report should not be empty"


def test_round_trip_does_not_raise_on_missing_file() -> None:
    result = round_trip(Path("/does/not/exist.CLF"), "digico_sd")
    assert result.error is not None


# --------------------------------------------------------------------------- #
# Fixture-golden pattern
# --------------------------------------------------------------------------- #


def test_fixture_golden_for_empty_calibration(empty_calibration_clf: Path) -> None:
    show = parse_yamaha_cl_binary(empty_calibration_clf)
    result = verify_against_fixture(show, "empty calibration file.CLF")
    assert result.fatal_error is None, (
        f"fixture verification setup failed: {result.fatal_error}"
    )
    failures = result.failed_checks
    assert not failures, (
        "fixture mismatches: "
        f"{[(c.channel_id, c.parameter, c.source_value, c.target_value) for c in failures[:5]]}"
    )


def test_fixture_missing_returns_fatal_error_not_raises() -> None:
    from models.universal import ShowFile

    empty_show = ShowFile(source_console="yamaha_cl")
    result = verify_against_fixture(empty_show, "no_such_sample_file.CLF")
    assert result.fatal_error is not None


# --------------------------------------------------------------------------- #
# Translator hook — non-blocking behaviour
# --------------------------------------------------------------------------- #


def test_translator_hook_logs_but_does_not_block(
    example1_clf: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """translate() must succeed even if the harness logs verification noise."""
    from translator import translate

    with caplog.at_level(logging.DEBUG, logger="engine.verification"):
        result = translate(
            source_file=example1_clf,
            source_console="yamaha_cl",
            target_console="digico_sd",
        )
    assert result.output_bytes  # translation itself succeeded
    # We don't assert specific log lines (the harness may pass cleanly),
    # only that nothing raised and the call returned normally.


# --------------------------------------------------------------------------- #
# EQ band checks
# --------------------------------------------------------------------------- #


from models.universal import Channel, ChannelColor, EQBand, EQBandType, Gate, Compressor, ShowFile
from verification.harness import _compare_channel


def _make_channel(id=1, eq_bands=None, gate=None, compressor=None):
    return Channel(
        id=id, name="TEST", color=ChannelColor.RED, input_patch=1,
        hpf_frequency=80.0, hpf_enabled=True,
        eq_bands=eq_bands or [], gate=gate, compressor=compressor,
    )


def test_compare_channel_eq_frequency_within_tolerance():
    band = EQBand(frequency=1000.0, gain=3.0, q=0.707, band_type=EQBandType.PEAK)
    tgt_band = EQBand(frequency=1000.5, gain=3.0, q=0.707, band_type=EQBandType.PEAK)
    src = _make_channel(eq_bands=[band])
    tgt = _make_channel(eq_bands=[tgt_band])
    checks = _compare_channel(src, tgt, "yamaha_cl_binary")
    freq_check = next(c for c in checks if c.parameter == "eq_band_1.frequency")
    assert freq_check.passed  # 0.5 Hz is within 1.0 Hz tolerance


def test_compare_channel_eq_frequency_outside_tolerance():
    band = EQBand(frequency=1000.0, gain=3.0, q=0.707, band_type=EQBandType.PEAK)
    tgt_band = EQBand(frequency=1005.0, gain=3.0, q=0.707, band_type=EQBandType.PEAK)
    src = _make_channel(eq_bands=[band])
    tgt = _make_channel(eq_bands=[tgt_band])
    checks = _compare_channel(src, tgt, "yamaha_cl_binary")
    freq_check = next(c for c in checks if c.parameter == "eq_band_1.frequency")
    assert not freq_check.passed


def test_compare_channel_eq_band_type_mismatch_is_not_failure():
    band = EQBand(frequency=100.0, gain=0.0, q=0.707, band_type=EQBandType.LOW_SHELF)
    tgt_band = EQBand(frequency=100.0, gain=0.0, q=0.707, band_type=EQBandType.PEAK)
    src = _make_channel(eq_bands=[band])
    tgt = _make_channel(eq_bands=[tgt_band])
    checks = _compare_channel(src, tgt, "yamaha_cl_binary")
    type_check = next(c for c in checks if c.parameter == "eq_band_1.band_type")
    assert type_check.passed  # approximation: not a hard failure
    assert "approximated" in type_check.note
