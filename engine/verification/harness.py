"""Verification harness V1.

Re-parses translation output and diffs it against the source ShowFile
on a per-parameter basis. Returns a structured ``HarnessResult`` with one
``ParameterCheck`` entry per (channel, parameter) pair examined.

Design constraints
------------------

* ``verify_translation`` MUST NOT raise. Any internal exception is captured
  as a failed ``ParameterCheck`` so the harness can be hooked into the
  translator without ever blocking a translation.
* Logging goes to ``engine.verification``. Callers that want quieter output
  can attach a ``NullHandler`` to that logger.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Union

from models.universal import Channel, ShowFile

logger = logging.getLogger("engine.verification")


# --------------------------------------------------------------------------- #
# Data structures
# --------------------------------------------------------------------------- #


@dataclass
class ParameterCheck:
    """Result of comparing a single parameter on a single channel."""

    channel_id: int
    parameter: str
    source_value: Any
    target_value: Any
    passed: bool
    note: str = ""


@dataclass
class HarnessResult:
    """Aggregate result of running the verification harness on a translation."""

    target_format: str
    checks: list[ParameterCheck] = field(default_factory=list)
    fatal_error: Optional[str] = None  # set if re-parse failed entirely

    @property
    def all_passed(self) -> bool:
        return self.fatal_error is None and all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> list[ParameterCheck]:
        return [c for c in self.checks if not c.passed]

    def summary(self) -> str:
        if self.fatal_error:
            return f"verification FAILED to run: {self.fatal_error}"
        passed = sum(1 for c in self.checks if c.passed)
        total = len(self.checks)
        return f"verification {passed}/{total} checks passed"


# --------------------------------------------------------------------------- #
# Parser registry — kept here (rather than importing translator.PARSERS) to
# avoid a circular import once translator.py imports this module.
# --------------------------------------------------------------------------- #


def _parser_for(target_format: str) -> Callable[[Path], ShowFile]:
    # Lazy imports keep this module importable even if a downstream parser
    # has problems at import time.
    if target_format == "digico_sd":
        from parsers.digico_sd import parse_digico_sd
        return parse_digico_sd
    if target_format == "yamaha_cl":
        # Use the same auto-detect logic as the translator.
        from translator import _parse_yamaha_auto
        return _parse_yamaha_auto
    raise ValueError(f"No verification parser registered for target format: {target_format!r}")


# --------------------------------------------------------------------------- #
# Per-parameter comparison
# --------------------------------------------------------------------------- #


def _compare_channel(
    source: Channel,
    target: Channel,
    target_format: str,
) -> list[ParameterCheck]:
    """Diff one source/target channel pair and return per-parameter checks."""

    checks: list[ParameterCheck] = []

    def add(parameter: str, sv: Any, tv: Any, passed: bool, note: str = "") -> None:
        checks.append(ParameterCheck(
            channel_id=source.id,
            parameter=parameter,
            source_value=sv,
            target_value=tv,
            passed=passed,
            note=note,
        ))

    add("name", source.name, target.name, source.name == target.name)
    add("color", source.color.value, target.color.value, source.color == target.color)

    # Input patch: DiGiCo writes "0" for unpatched and the parser reads that
    # back as None — so None vs None and int vs int are both fine.
    add(
        "input_patch",
        source.input_patch,
        target.input_patch,
        source.input_patch == target.input_patch,
    )

    add(
        "hpf_enabled",
        source.hpf_enabled,
        target.hpf_enabled,
        source.hpf_enabled == target.hpf_enabled,
    )
    add(
        "hpf_frequency",
        source.hpf_frequency,
        target.hpf_frequency,
        _floats_equal(source.hpf_frequency, target.hpf_frequency),
    )

    # Mute state is known to be dropped by DiGiCo — flag as informational
    # rather than a hard failure when target format can't carry it.
    if target_format == "digico_sd" and source.muted and not target.muted:
        add(
            "muted",
            source.muted,
            target.muted,
            False,
            note="muted state cannot be represented in DiGiCo XML (known drop)",
        )
    else:
        add("muted", source.muted, target.muted, source.muted == target.muted)

    return checks


def _floats_equal(a: float, b: float, tol: float = 1e-3) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return a == b


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def verify_translation(
    source_show: ShowFile,
    output: Union[bytes, Path, str],
    target_format: str,
) -> HarnessResult:
    """Re-parse ``output`` and diff against ``source_show``, per parameter.

    Parameters
    ----------
    source_show:
        The universal ShowFile produced by parsing the original input.
    output:
        Either the raw bytes produced by the writer, or a path to a file that
        already contains those bytes. Bytes are written to a temporary file
        before being handed to the target parser, since most parsers expect
        file paths.
    target_format:
        Key matching ``translator.PARSERS`` (e.g. "digico_sd", "yamaha_cl").

    Returns
    -------
    HarnessResult
        Always returned. Internal failures populate ``fatal_error`` rather
        than raising — this method is safe to call from the translator hook.
    """

    result = HarnessResult(target_format=target_format)
    tmp_path: Optional[Path] = None

    try:
        parser = _parser_for(target_format)

        if isinstance(output, (bytes, bytearray)):
            # Pick a writable suffix the target parser will accept.
            suffix = ".show" if target_format == "digico_sd" else ".cle"
            fd, name = tempfile.mkstemp(suffix=suffix, prefix="verify_")
            os.close(fd)
            tmp_path = Path(name)
            tmp_path.write_bytes(bytes(output))
            target_path = tmp_path
        else:
            target_path = Path(output)

        target_show = parser(target_path)

        # Channel-count check is its own parameter so it shows up in reports.
        result.checks.append(ParameterCheck(
            channel_id=0,
            parameter="channel_count",
            source_value=len(source_show.channels),
            target_value=len(target_show.channels),
            passed=len(source_show.channels) == len(target_show.channels),
        ))

        # Pair channels by ID where possible; otherwise zip in order.
        target_by_id = {ch.id: ch for ch in target_show.channels}
        for src_ch in source_show.channels:
            tgt_ch = target_by_id.get(src_ch.id)
            if tgt_ch is None:
                result.checks.append(ParameterCheck(
                    channel_id=src_ch.id,
                    parameter="channel_present",
                    source_value=True,
                    target_value=False,
                    passed=False,
                    note="channel id missing after round-trip",
                ))
                continue
            result.checks.extend(_compare_channel(src_ch, tgt_ch, target_format))

    except Exception as exc:  # noqa: BLE001 — harness must never raise
        result.fatal_error = f"{type(exc).__name__}: {exc}"
        logger.warning("verification harness fatal error: %s", result.fatal_error)
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass

    if not result.all_passed:
        logger.info(
            "verification result: %s (failed=%d)",
            result.summary(),
            len(result.failed_checks),
        )
    else:
        logger.debug("verification result: %s", result.summary())

    return result


# --------------------------------------------------------------------------- #
# Fixture-golden support
# --------------------------------------------------------------------------- #
#
# For each calibration file in samples/, expected parameter values can be
# stored in engine/verification/fixtures/<filename>.yaml. The fixture format
# is intentionally shallow — only fields explicitly listed are checked, so a
# fixture can grow incrementally as more parameters are validated against
# real-console behaviour.
#
# Currently demonstrated by ``empty calibration file.CLF.yaml`` which only
# pins channel_count and channel_names. More fixtures (and more fields per
# fixture) will be added per parameter class as the harness matures.

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(sample_filename: str) -> Optional[dict]:
    """Load a fixture YAML for a given sample file. Returns None if absent."""
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        logger.warning("PyYAML not installed; cannot load fixture %s", sample_filename)
        return None

    fixture_path = FIXTURES_DIR / f"{sample_filename}.yaml"
    if not fixture_path.exists():
        return None
    with open(fixture_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def verify_against_fixture(show: ShowFile, sample_filename: str) -> HarnessResult:
    """Compare a parsed ShowFile against a golden fixture YAML.

    Returns a ``HarnessResult`` with one ParameterCheck per fixture field.
    Fields not present in the fixture are skipped (allow incremental fixtures).
    Returns a result with a fatal_error if the fixture is missing or unloadable.
    """

    result = HarnessResult(target_format="<fixture>")
    try:
        fixture = load_fixture(sample_filename)
        if fixture is None:
            result.fatal_error = f"no fixture for {sample_filename}"
            return result

        if "channel_count" in fixture:
            actual = len(show.channels)
            expected = fixture["channel_count"]
            result.checks.append(ParameterCheck(
                channel_id=0,
                parameter="channel_count",
                source_value=expected,
                target_value=actual,
                passed=expected == actual,
            ))

        if "channel_names" in fixture:
            expected_names = fixture["channel_names"]
            for idx, expected_name in enumerate(expected_names):
                if idx >= len(show.channels):
                    result.checks.append(ParameterCheck(
                        channel_id=idx + 1,
                        parameter="name",
                        source_value=expected_name,
                        target_value=None,
                        passed=False,
                        note="channel missing",
                    ))
                    continue
                actual_name = show.channels[idx].name
                result.checks.append(ParameterCheck(
                    channel_id=show.channels[idx].id,
                    parameter="name",
                    source_value=expected_name,
                    target_value=actual_name,
                    passed=expected_name == actual_name,
                ))

    except Exception as exc:  # noqa: BLE001
        result.fatal_error = f"{type(exc).__name__}: {exc}"
        logger.warning("fixture verification fatal error: %s", result.fatal_error)

    return result
