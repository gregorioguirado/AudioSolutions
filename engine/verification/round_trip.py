"""Round-trip translation verification.

Performs:

    source_path -> source parser -> ShowFile A
    ShowFile A  -> target writer  -> bytes
    bytes       -> target parser  -> ShowFile B
    diff(A, B)

Returns a structured ``RoundTripResult`` so test code (and the harness hook)
can introspect what survived the trip and what didn't. The function NEVER
raises — internal failures are reported via the ``diff_report`` and the
``error`` field of the result.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from models.universal import ShowFile

from .harness import HarnessResult, verify_translation

logger = logging.getLogger("engine.verification")


@dataclass
class RoundTripResult:
    """Outcome of a parse → write → re-parse round trip."""

    source_path: Path
    target_format: str
    source_show: Optional[ShowFile] = None
    intermediate_show: Optional[ShowFile] = None
    diff_report: list[dict] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def all_passed(self) -> bool:
        return self.error is None and all(d.get("passed", False) for d in self.diff_report)

    @property
    def failures(self) -> list[dict]:
        return [d for d in self.diff_report if not d.get("passed", False)]


# --------------------------------------------------------------------------- #
# Source parser registry
# --------------------------------------------------------------------------- #


def _detect_source_format(source_path: Path) -> str:
    """Heuristically detect a source-format key from extension."""
    suffix = source_path.suffix.lower()
    if suffix in (".clf", ".cle"):
        return "yamaha_cl"
    if suffix in (".show", ".xml"):
        return "digico_sd"
    raise ValueError(f"Cannot auto-detect source format for {source_path.name!r}")


def _source_parser_for(source_format: str) -> Callable[[Path], ShowFile]:
    if source_format == "yamaha_cl":
        from translator import _parse_yamaha_auto
        return _parse_yamaha_auto
    if source_format == "digico_sd":
        from parsers.digico_sd import parse_digico_sd
        return parse_digico_sd
    raise ValueError(f"No source parser registered for {source_format!r}")


def _target_writer_for(target_format: str) -> Callable[[ShowFile], bytes]:
    if target_format == "digico_sd":
        from writers.digico_sd import write_digico_sd
        return write_digico_sd
    if target_format == "yamaha_cl":
        from writers.yamaha_cl import write_yamaha_cl
        return write_yamaha_cl
    raise ValueError(f"No target writer registered for {target_format!r}")


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def round_trip(
    source_path: Path,
    target_format: str,
    source_format: Optional[str] = None,
) -> RoundTripResult:
    """Round-trip ``source_path`` through ``target_format`` and diff the result.

    Parameters
    ----------
    source_path:
        Path to the original show file.
    target_format:
        Console key for the writer/parser pair under test (e.g. "digico_sd").
    source_format:
        Optional override for the source format. If omitted it's inferred
        from the file extension.

    Returns
    -------
    RoundTripResult
        Always returned. ``error`` will be set if the trip blew up before a
        diff could be produced.
    """

    result = RoundTripResult(source_path=source_path, target_format=target_format)

    try:
        src_fmt = source_format or _detect_source_format(source_path)
        parser = _source_parser_for(src_fmt)
        writer = _target_writer_for(target_format)
    except Exception as exc:  # noqa: BLE001
        result.error = f"setup error: {type(exc).__name__}: {exc}"
        logger.warning("round_trip setup failed: %s", result.error)
        return result

    # Parse source.
    try:
        source_show = parser(source_path)
        result.source_show = source_show
    except Exception as exc:  # noqa: BLE001
        result.error = f"source parse error: {type(exc).__name__}: {exc}"
        logger.warning("round_trip source parse failed: %s", result.error)
        return result

    # Write to bytes, then re-parse.
    tmp_path: Optional[Path] = None
    try:
        output_bytes = writer(source_show)
        suffix = ".show" if target_format == "digico_sd" else ".cle"
        fd, name = tempfile.mkstemp(suffix=suffix, prefix="roundtrip_")
        os.close(fd)
        tmp_path = Path(name)
        tmp_path.write_bytes(output_bytes)

        target_parser = _source_parser_for(target_format)  # parser keyed same as source
        intermediate_show = target_parser(tmp_path)
        result.intermediate_show = intermediate_show
    except Exception as exc:  # noqa: BLE001
        result.error = f"write/re-parse error: {type(exc).__name__}: {exc}"
        logger.warning("round_trip write/reparse failed: %s", result.error)
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass
        return result
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    # Build a diff report by reusing the harness comparator.
    harness: HarnessResult = verify_translation(source_show, output_bytes, target_format)
    if harness.fatal_error:
        result.error = f"harness error: {harness.fatal_error}"
        return result

    result.diff_report = [
        {
            "channel_id": c.channel_id,
            "parameter": c.parameter,
            "source_value": c.source_value,
            "target_value": c.target_value,
            "passed": c.passed,
            "note": c.note,
        }
        for c in harness.checks
    ]

    return result
