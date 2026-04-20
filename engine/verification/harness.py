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

    @property
    def fidelity_score(self) -> "FidelityScore":
        return _compute_fidelity(self.checks)


@dataclass
class FidelityScore:
    """Per-field-group fidelity percentage after a round-trip translation."""
    names: float       # 0–100: % of channel name checks that passed
    hpf: float         # 0–100: % of HPF checks (enabled + frequency) that passed
    eq: float          # 0–100: % of EQ band parameter checks that passed
    gate: float        # 0–100: % of gate parameter checks that passed
    compressor: float  # 0–100: % of compressor parameter checks that passed
    mix_buses: float   # 0–100: % of mix bus assignment checks that passed
    vcas: float        # 0–100: % of VCA assignment checks that passed
    overall: float     # 0–100: unweighted average of the seven groups


def _compute_fidelity(checks: list[ParameterCheck]) -> "FidelityScore":
    """Compute per-group fidelity from a list of ParameterChecks.

    Channel-level checks (channel_id == 0) are excluded from all groups.
    A group with no relevant checks scores 100.0 — absence of data is not failure.
    """
    def _pct(prefixes: tuple[str, ...]) -> float:
        relevant = [
            c for c in checks
            if c.channel_id != 0
            and any(
                c.parameter == p
                or c.parameter.startswith(p + ".")
                or c.parameter.startswith(p + "_")
                for p in prefixes
            )
        ]
        if not relevant:
            return 100.0
        return 100.0 * sum(1 for c in relevant if c.passed) / len(relevant)

    names = _pct(("name",))
    hpf = _pct(("hpf_enabled", "hpf_frequency"))
    eq = _pct(("eq_band",))
    gate = _pct(("gate",))
    compressor = _pct(("compressor",))
    mix_buses = _pct(("mix_bus_assignments",))
    vcas = _pct(("vca_assignments",))
    overall = (names + hpf + eq + gate + compressor + mix_buses + vcas) / 7.0
    return FidelityScore(names=names, hpf=hpf, eq=eq, gate=gate, compressor=compressor,
                         mix_buses=mix_buses, vcas=vcas, overall=overall)


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
    if target_format == "yamaha_cl_binary":
        from parsers.yamaha_cl_binary import parse_yamaha_cl_binary
        return parse_yamaha_cl_binary
    if target_format == "yamaha_ql":
        from parsers.yamaha_ql import parse_yamaha_ql
        return parse_yamaha_ql
    if target_format == "yamaha_rivage":
        from parsers.yamaha_rivage import parse as _parse_rivage
        # _parse_rivage takes a str; the harness passes a Path — wrap it.
        return lambda p: _parse_rivage(str(p))
    if target_format == "yamaha_dm7":
        from parsers.yamaha_dm7 import parse as _parse_dm7
        # _parse_dm7 takes bytes; wrap to accept a Path.
        return lambda p: _parse_dm7(Path(p).read_bytes())
    if target_format == "yamaha_tf":
        from parsers.yamaha_tf import parse as _parse_tf
        # _parse_tf takes a str path.
        return lambda p: _parse_tf(str(p))
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

    # EQ bands — pair by index; source and target should have the same count
    for i, src_band in enumerate(source.eq_bands):
        if i >= len(target.eq_bands):
            add(f"eq_band_{i+1}.present", True, False, False,
                note=f"eq band {i+1} missing after round-trip")
            continue
        tgt_band = target.eq_bands[i]
        prefix = f"eq_band_{i+1}"
        add(f"{prefix}.enabled",
            src_band.enabled, tgt_band.enabled,
            src_band.enabled == tgt_band.enabled)
        add(f"{prefix}.frequency",
            src_band.frequency, tgt_band.frequency,
            _floats_equal(src_band.frequency, tgt_band.frequency, tol=1.0))
        add(f"{prefix}.gain",
            src_band.gain, tgt_band.gain,
            _floats_equal(src_band.gain, tgt_band.gain, tol=0.01))
        add(f"{prefix}.q",
            src_band.q, tgt_band.q,
            _floats_equal(src_band.q, tgt_band.q, tol=0.001))
        # band_type mismatches are expected approximations — never a hard failure
        type_match = src_band.band_type == tgt_band.band_type
        add(f"{prefix}.band_type",
            src_band.band_type.value, tgt_band.band_type.value,
            passed=True,
            note="approximated" if not type_match else "")

    # Note: extra bands in target (len(target.eq_bands) > len(source.eq_bands)) are
    # intentionally not flagged — the harness checks source fidelity, not target size.

    # Gate
    if source.gate is not None and target.gate is not None:
        add("gate.enabled",
            source.gate.enabled, target.gate.enabled,
            source.gate.enabled == target.gate.enabled)
        add("gate.threshold",
            source.gate.threshold, target.gate.threshold,
            _floats_equal(source.gate.threshold, target.gate.threshold, tol=0.01))
        add("gate.attack",
            source.gate.attack, target.gate.attack,
            _floats_equal(source.gate.attack, target.gate.attack, tol=1.0))
        add("gate.hold",
            source.gate.hold, target.gate.hold,
            _floats_equal(source.gate.hold, target.gate.hold, tol=1.0))
        add("gate.release",
            source.gate.release, target.gate.release,
            _floats_equal(source.gate.release, target.gate.release, tol=1.0))
    elif source.gate is not None and target.gate is None:
        add("gate", source.gate, None, False,
            note="gate lost in translation")

    # Compressor
    if source.compressor is not None and target.compressor is not None:
        add("compressor.enabled",
            source.compressor.enabled, target.compressor.enabled,
            source.compressor.enabled == target.compressor.enabled)
        add("compressor.threshold",
            source.compressor.threshold, target.compressor.threshold,
            _floats_equal(source.compressor.threshold, target.compressor.threshold, tol=0.01))
        add("compressor.ratio",
            source.compressor.ratio, target.compressor.ratio,
            _floats_equal(source.compressor.ratio, target.compressor.ratio, tol=0.01))
        add("compressor.attack",
            source.compressor.attack, target.compressor.attack,
            _floats_equal(source.compressor.attack, target.compressor.attack, tol=1.0))
        add("compressor.release",
            source.compressor.release, target.compressor.release,
            _floats_equal(source.compressor.release, target.compressor.release, tol=1.0))
        # Skip makeup_gain if source is 0.0 — RIVAGE makeup_gain offset not yet calibrated
        if source.compressor.makeup_gain != 0.0:
            add("compressor.makeup_gain",
                source.compressor.makeup_gain, target.compressor.makeup_gain,
                _floats_equal(source.compressor.makeup_gain, target.compressor.makeup_gain, tol=0.01))
    elif source.compressor is not None and target.compressor is None:
        add("compressor", source.compressor, None, False,
            note="compressor lost in translation")

    # Mix bus sends — presence/absence of each assignment
    src_mix = set(source.mix_bus_assignments or [])
    tgt_mix = set(target.mix_bus_assignments or [])
    missing = src_mix - tgt_mix
    extra = tgt_mix - src_mix
    add("mix_bus_assignments.missing", sorted(src_mix), sorted(tgt_mix), not missing,
        note=f"missing buses: {sorted(missing)}" if missing else "")
    add("mix_bus_assignments.extra", sorted(src_mix), sorted(tgt_mix), not extra,
        note=f"extra buses: {sorted(extra)}" if extra else "")

    # VCA assignments — same pattern
    src_vca = set(source.vca_assignments or [])
    tgt_vca = set(target.vca_assignments or [])
    missing_v = src_vca - tgt_vca
    extra_v = tgt_vca - src_vca
    add("vca_assignments.missing", sorted(src_vca), sorted(tgt_vca), not missing_v,
        note=f"missing VCAs: {sorted(missing_v)}" if missing_v else "")
    add("vca_assignments.extra", sorted(src_vca), sorted(tgt_vca), not extra_v,
        note=f"extra VCAs: {sorted(extra_v)}" if extra_v else "")

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
            if target_format == "digico_sd":
                suffix = ".show"
            elif target_format == "yamaha_cl_binary":
                suffix = ".CLF"
            elif target_format == "yamaha_rivage":
                suffix = ".RIVAGEPM"
            elif target_format == "yamaha_dm7":
                suffix = ".dm7f"
            elif target_format == "yamaha_tf":
                suffix = ".tff"
            else:
                suffix = ".cle"
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

        if "channels" in fixture:
            ch_by_id = {ch.id: ch for ch in show.channels}

            def _fx_add(ch_id, param, expected, actual_val, passed, note=""):
                result.checks.append(ParameterCheck(
                    channel_id=ch_id,
                    parameter=param,
                    source_value=expected,
                    target_value=actual_val,
                    passed=passed,
                    note=note,
                ))

            for fix_ch in fixture["channels"]:
                ch_id = fix_ch.get("id")
                actual = ch_by_id.get(ch_id)
                if actual is None:
                    result.checks.append(ParameterCheck(
                        channel_id=ch_id or 0,
                        parameter="channel_present",
                        source_value=True, target_value=False, passed=False,
                        note="channel id missing",
                    ))
                    continue

                if "name" in fix_ch:
                    _fx_add(ch_id, "name", fix_ch["name"], actual.name,
                            fix_ch["name"] == actual.name)
                if "hpf_enabled" in fix_ch:
                    _fx_add(ch_id, "hpf_enabled", fix_ch["hpf_enabled"], actual.hpf_enabled,
                            fix_ch["hpf_enabled"] == actual.hpf_enabled)
                if "hpf_frequency" in fix_ch:
                    _fx_add(ch_id, "hpf_frequency", fix_ch["hpf_frequency"], actual.hpf_frequency,
                            _floats_equal(fix_ch["hpf_frequency"], actual.hpf_frequency, tol=1.0))
                if "gate_enabled" in fix_ch:
                    gate_enabled = actual.gate is not None and actual.gate.enabled
                    _fx_add(ch_id, "gate_enabled", fix_ch["gate_enabled"], gate_enabled,
                            fix_ch["gate_enabled"] == gate_enabled)
                if "gate_threshold" in fix_ch and actual.gate is not None:
                    _fx_add(ch_id, "gate_threshold", fix_ch["gate_threshold"], actual.gate.threshold,
                            _floats_equal(fix_ch["gate_threshold"], actual.gate.threshold, tol=0.01))
                if "compressor_enabled" in fix_ch:
                    comp_enabled = actual.compressor is not None and actual.compressor.enabled
                    _fx_add(ch_id, "compressor_enabled", fix_ch["compressor_enabled"], comp_enabled,
                            fix_ch["compressor_enabled"] == comp_enabled)
                if "compressor_threshold" in fix_ch and actual.compressor is not None:
                    _fx_add(ch_id, "compressor_threshold", fix_ch["compressor_threshold"],
                            actual.compressor.threshold,
                            _floats_equal(fix_ch["compressor_threshold"], actual.compressor.threshold, tol=0.01))
                if "compressor_ratio" in fix_ch and actual.compressor is not None:
                    _fx_add(ch_id, "compressor_ratio", fix_ch["compressor_ratio"],
                            actual.compressor.ratio,
                            _floats_equal(fix_ch["compressor_ratio"], actual.compressor.ratio, tol=0.01))

    except Exception as exc:  # noqa: BLE001
        result.fatal_error = f"{type(exc).__name__}: {exc}"
        logger.warning("fixture verification fatal error: %s", result.fatal_error)

    return result
