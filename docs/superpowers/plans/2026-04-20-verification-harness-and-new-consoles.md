# Verification Harness Extensions + New Consoles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the verification harness to validate EQ, gate, and compressor parameters after round-trip; add a fidelity score; lock all sample files as regression baselines; add Yamaha QL and A&H dLive (skeleton) console support.

**Architecture:** Extend `engine/verification/harness.py` with richer per-parameter checks and a `FidelityScore` dataclass; wire the score into `TranslationResult` so the API can return it. New console parsers are thin wrappers (`yamaha_ql`) or stubs (`ah_dlive`) registered in `translator.PARSERS`.

**Tech Stack:** Python 3.11, pytest, PyYAML, existing `models.universal` dataclasses, existing `engine/verification/harness.py`.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `engine/verification/harness.py` | Modify | Add EQ/gate/comp checks; add `FidelityScore`; add `fidelity_score` property to `HarnessResult` |
| `engine/translator.py` | Modify | Add `parse_gate_passed` + `fidelity_score` fields to `TranslationResult`; populate from harness result |
| `engine/verification/fixtures/*.yaml` | Create (many) | One fixture per sample file — regression baselines |
| `engine/tests/verification/test_harness.py` | Modify | Extend `verify_against_fixture` checks; add parametrize fixture suite test |
| `tools/generate_fixtures.py` | Create | Script to parse all sample files and print starter YAML |
| `engine/parsers/yamaha_ql.py` | Create | Thin wrapper over `parse_yamaha_cl_binary`, sets `source_console="yamaha_ql"` |
| `engine/parsers/ah_dlive.py` | Create | `NotImplementedError` stub registered so the console appears in PARSERS |
| `engine/writers/ah_dlive.py` | Create | `NotImplementedError` stub registered in WRITERS |

---

## Task 1: Extend `_compare_channel()` with EQ band checks

**Files:**
- Modify: `engine/verification/harness.py:99-156`
- Test: `engine/tests/verification/test_harness.py`

- [ ] **Step 1: Write the failing tests**

Add to `engine/tests/verification/test_harness.py`:

```python
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
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd engine && python -m pytest tests/verification/test_harness.py::test_compare_channel_eq_frequency_within_tolerance tests/verification/test_harness.py::test_compare_channel_eq_frequency_outside_tolerance tests/verification/test_harness.py::test_compare_channel_eq_band_type_mismatch_is_not_failure -v
```

Expected: `FAILED` — `_compare_channel` does not yet produce `eq_band_1.*` checks.

- [ ] **Step 3: Add EQ band checks to `_compare_channel()` in `harness.py`**

After the `muted` block (line ~154), add:

```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd engine && python -m pytest tests/verification/test_harness.py::test_compare_channel_eq_frequency_within_tolerance tests/verification/test_harness.py::test_compare_channel_eq_frequency_outside_tolerance tests/verification/test_harness.py::test_compare_channel_eq_band_type_mismatch_is_not_failure -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
cd engine && python -m pytest tests/ -q
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add engine/verification/harness.py engine/tests/verification/test_harness.py
git commit -m "feat(harness): add EQ band parameter checks to _compare_channel"
```

---

## Task 2: Add gate and compressor checks to `_compare_channel()`

**Files:**
- Modify: `engine/verification/harness.py`
- Test: `engine/tests/verification/test_harness.py`

- [ ] **Step 1: Write the failing tests**

Add to `engine/tests/verification/test_harness.py`:

```python
def test_compare_channel_gate_threshold_passes_within_tolerance():
    gate = Gate(threshold=-30.0, attack=1.0, hold=50.0, release=200.0, enabled=True)
    tgt_gate = Gate(threshold=-30.005, attack=1.0, hold=50.0, release=200.0, enabled=True)
    src = _make_channel(gate=gate)
    tgt = _make_channel(gate=tgt_gate)
    checks = _compare_channel(src, tgt, "yamaha_cl_binary")
    thr = next(c for c in checks if c.parameter == "gate.threshold")
    assert thr.passed

def test_compare_channel_gate_missing_on_target_fails():
    gate = Gate(threshold=-30.0, attack=1.0, hold=50.0, release=200.0, enabled=True)
    src = _make_channel(gate=gate)
    tgt = _make_channel(gate=None)
    checks = _compare_channel(src, tgt, "yamaha_cl_binary")
    gate_check = next(c for c in checks if c.parameter == "gate")
    assert not gate_check.passed

def test_compare_channel_compressor_ratio_within_tolerance():
    comp = Compressor(threshold=-18.0, ratio=4.0, attack=10.0, release=200.0, makeup_gain=3.0, enabled=True)
    tgt_comp = Compressor(threshold=-18.0, ratio=4.005, attack=10.0, release=200.0, makeup_gain=3.0, enabled=True)
    src = _make_channel(compressor=comp)
    tgt = _make_channel(compressor=tgt_comp)
    checks = _compare_channel(src, tgt, "yamaha_cl_binary")
    ratio_check = next(c for c in checks if c.parameter == "compressor.ratio")
    assert ratio_check.passed

def test_compare_channel_compressor_makeup_gain_skipped_when_source_is_zero():
    comp = Compressor(threshold=-18.0, ratio=4.0, attack=10.0, release=200.0, makeup_gain=0.0, enabled=True)
    tgt_comp = Compressor(threshold=-18.0, ratio=4.0, attack=10.0, release=200.0, makeup_gain=5.0, enabled=True)
    src = _make_channel(compressor=comp)
    tgt = _make_channel(compressor=tgt_comp)
    checks = _compare_channel(src, tgt, "yamaha_cl_binary")
    # makeup_gain skipped when source is 0.0 (RIVAGE calibration gap)
    assert not any(c.parameter == "compressor.makeup_gain" for c in checks)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd engine && python -m pytest tests/verification/test_harness.py::test_compare_channel_gate_threshold_passes_within_tolerance tests/verification/test_harness.py::test_compare_channel_gate_missing_on_target_fails tests/verification/test_harness.py::test_compare_channel_compressor_ratio_within_tolerance tests/verification/test_harness.py::test_compare_channel_compressor_makeup_gain_skipped_when_source_is_zero -v
```

Expected: 4 FAILED.

- [ ] **Step 3: Add gate and compressor checks to `_compare_channel()` in `harness.py`**

After the EQ bands block you added in Task 1, add:

```python
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
```

- [ ] **Step 4: Run tests**

```bash
cd engine && python -m pytest tests/verification/test_harness.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Run full suite**

```bash
cd engine && python -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add engine/verification/harness.py engine/tests/verification/test_harness.py
git commit -m "feat(harness): add gate and compressor parameter checks to _compare_channel"
```

---

## Task 3: Add `FidelityScore` and wire into `HarnessResult` + `TranslationResult`

**Files:**
- Modify: `engine/verification/harness.py`
- Modify: `engine/translator.py`
- Test: `engine/tests/verification/test_harness.py`

- [ ] **Step 1: Write failing tests for FidelityScore**

Add to `engine/tests/verification/test_harness.py`:

```python
from verification.harness import FidelityScore, HarnessResult, ParameterCheck

def test_harness_result_has_fidelity_score():
    result = HarnessResult(target_format="yamaha_cl_binary")
    result.checks = [
        ParameterCheck(channel_id=1, parameter="name", source_value="A", target_value="A", passed=True),
        ParameterCheck(channel_id=1, parameter="hpf_enabled", source_value=True, target_value=True, passed=True),
        ParameterCheck(channel_id=1, parameter="hpf_frequency", source_value=80.0, target_value=80.0, passed=True),
        ParameterCheck(channel_id=1, parameter="eq_band_1.frequency", source_value=1000.0, target_value=999.0, passed=True),
        ParameterCheck(channel_id=1, parameter="gate.threshold", source_value=-30.0, target_value=-30.0, passed=True),
        ParameterCheck(channel_id=1, parameter="compressor.ratio", source_value=4.0, target_value=4.0, passed=True),
    ]
    score = result.fidelity_score
    assert isinstance(score, FidelityScore)
    assert score.names == 100.0
    assert score.hpf == 100.0
    assert score.eq == 100.0
    assert score.gate == 100.0
    assert score.compressor == 100.0
    assert score.overall == 100.0

def test_fidelity_score_partial_failure():
    result = HarnessResult(target_format="yamaha_cl_binary")
    result.checks = [
        ParameterCheck(channel_id=1, parameter="name", source_value="A", target_value="B", passed=False),
        ParameterCheck(channel_id=2, parameter="name", source_value="C", target_value="C", passed=True),
        ParameterCheck(channel_id=1, parameter="gate.threshold", source_value=-30.0, target_value=-35.0, passed=False),
        ParameterCheck(channel_id=1, parameter="gate.attack", source_value=1.0, target_value=1.0, passed=True),
    ]
    score = result.fidelity_score
    assert score.names == 50.0   # 1/2 passed
    assert score.gate == 50.0    # 1/2 passed
    assert score.hpf == 100.0    # no HPF checks = not a failure
    assert score.eq == 100.0     # no EQ checks = not a failure
    assert score.compressor == 100.0
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd engine && python -m pytest tests/verification/test_harness.py::test_harness_result_has_fidelity_score tests/verification/test_harness.py::test_fidelity_score_partial_failure -v
```

Expected: `FAILED` — `FidelityScore` not yet defined, `HarnessResult` has no `fidelity_score`.

- [ ] **Step 3: Add `FidelityScore` dataclass and `_compute_fidelity()` to `harness.py`**

After the `HarnessResult` class (around line 70), add:

```python
@dataclass
class FidelityScore:
    """Per-field-group fidelity percentage after a round-trip translation."""
    names: float       # 0–100: % of channel name checks that passed
    hpf: float         # 0–100: % of HPF checks (enabled + frequency) that passed
    eq: float          # 0–100: % of EQ band parameter checks that passed
    gate: float        # 0–100: % of gate parameter checks that passed
    compressor: float  # 0–100: % of compressor parameter checks that passed
    overall: float     # 0–100: unweighted average of the five groups


def _compute_fidelity(checks: list[ParameterCheck]) -> FidelityScore:
    """Compute per-group fidelity from a list of ParameterChecks.

    Channel-level checks (channel_id == 0) are excluded from all groups.
    A group with no relevant checks scores 100.0 — absence of data is not failure.
    """
    def _pct(prefixes: tuple[str, ...]) -> float:
        relevant = [
            c for c in checks
            if c.channel_id != 0
            and any(c.parameter == p or c.parameter.startswith(p + ".") or c.parameter.startswith(p + "_")
                    for p in prefixes)
        ]
        if not relevant:
            return 100.0
        return 100.0 * sum(1 for c in relevant if c.passed) / len(relevant)

    names = _pct(("name",))
    hpf = _pct(("hpf_enabled", "hpf_frequency"))
    eq = _pct(("eq_band",))
    gate = _pct(("gate",))
    compressor = _pct(("compressor",))
    overall = (names + hpf + eq + gate + compressor) / 5.0
    return FidelityScore(names=names, hpf=hpf, eq=eq, gate=gate, compressor=compressor, overall=overall)
```

Then add `fidelity_score` as a property on `HarnessResult` (inside the class, after `summary()`):

```python
    @property
    def fidelity_score(self) -> "FidelityScore":
        return _compute_fidelity(self.checks)
```

- [ ] **Step 4: Run tests**

```bash
cd engine && python -m pytest tests/verification/test_harness.py::test_harness_result_has_fidelity_score tests/verification/test_harness.py::test_fidelity_score_partial_failure -v
```

Expected: 2 PASSED.

- [ ] **Step 5: Add `parse_gate_passed` + `fidelity_score` to `TranslationResult` in `translator.py`**

Change the `TranslationResult` dataclass (lines 23–31):

```python
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from verification.harness import FidelityScore

@dataclass
class TranslationResult:
    output_bytes: bytes
    channel_count: int
    translated_parameters: list[str] = field(default_factory=list)
    approximated_parameters: list[str] = field(default_factory=list)
    dropped_parameters: list[str] = field(default_factory=list)
    channels: list = field(default_factory=list)
    parse_gate_passed: bool = True
    fidelity_score: Optional[object] = None  # FidelityScore at runtime
```

- [ ] **Step 6: Populate `parse_gate_passed` and `fidelity_score` from the harness hook in `translator.py`**

Replace the harness hook block (lines ~131–152) with:

```python
    parse_gate_passed = True
    fidelity_score = None
    try:
        from verification.harness import verify_translation
        harness_result = verify_translation(show, output_bytes, target_console)
        parse_gate_passed = harness_result.fatal_error is None
        fidelity_score = harness_result.fidelity_score
        if harness_result.fatal_error:
            logger.warning(
                "translation harness fatal error (%s -> %s): %s",
                source_console, target_console, harness_result.fatal_error,
            )
        elif not harness_result.all_passed:
            failed = harness_result.failed_checks
            logger.info(
                "translation harness reported %d failed check(s) (%s -> %s); first few: %s",
                len(failed), source_console, target_console,
                [(c.channel_id, c.parameter, c.note) for c in failed[:5]],
            )
        else:
            logger.debug(
                "translation harness clean (%s -> %s): %s",
                source_console, target_console, harness_result.summary(),
            )
    except Exception as exc:
        logger.warning("translation harness hook crashed (ignored): %s", exc)
```

And update the return at the end of `translate()`:

```python
    return TranslationResult(
        output_bytes=output_bytes,
        channel_count=len(show.channels),
        translated_parameters=_collect_translated_parameters(show),
        approximated_parameters=approximated,
        dropped_parameters=show.dropped_parameters,
        channels=show.channels,
        parse_gate_passed=parse_gate_passed,
        fidelity_score=fidelity_score,
    )
```

- [ ] **Step 7: Run full suite**

```bash
cd engine && python -m pytest tests/ -q
```

Expected: all pass. Verify `TranslationResult` has `parse_gate_passed` and `fidelity_score` attributes.

- [ ] **Step 8: Commit**

```bash
git add engine/verification/harness.py engine/translator.py engine/tests/verification/test_harness.py
git commit -m "feat(harness): add FidelityScore; wire parse_gate_passed + fidelity_score into TranslationResult"
```

---

## Task 4: Create fixture generator tool

**Files:**
- Create: `tools/generate_fixtures.py`

- [ ] **Step 1: Create `tools/generate_fixtures.py`**

```python
#!/usr/bin/env python3
"""Generate starter YAML fixtures for all sample files.

Run from the repo root:
    python tools/generate_fixtures.py

Prints YAML to stdout for each sample file. Redirect to fixture files:
    python tools/generate_fixtures.py > /dev/null  # just validate
    python tools/generate_fixtures.py 2>&1         # see per-file output

Each fixture captures: channel_count, first 5 channels with name, hpf,
gate threshold, compressor threshold/ratio (when present). These become
the regression baselines for the parametrize test in Task 5.
"""

import sys
import os
from pathlib import Path

# Add engine to path so parsers import cleanly
sys.path.insert(0, str(Path(__file__).parent.parent / "engine"))

from parsers.yamaha_cl_binary import parse_yamaha_cl_binary
from parsers.yamaha_cl import parse_yamaha_cl
from parsers import yamaha_dm7, yamaha_tf, yamaha_rivage

SAMPLES = Path(__file__).parent.parent / "samples"
FIXTURES = Path(__file__).parent.parent / "engine" / "verification" / "fixtures"

EXTENSION_PARSER = {
    ".CLF": lambda p: (parse_yamaha_cl_binary(p), "yamaha_cl"),
    ".CLE": lambda p: (_parse_cle(p), "yamaha_cl"),
    ".dm7f": lambda p: (yamaha_dm7.parse(p.read_bytes()), "yamaha_dm7"),
    ".tff": lambda p: (yamaha_tf.parse(str(p)), "yamaha_tf"),
    ".RIVAGEPM": lambda p: (yamaha_rivage.parse(str(p)), "yamaha_rivage_pm"),
}


def _parse_cle(path: Path):
    with open(path, "rb") as f:
        header = f.read(2)
    if header == b"PK":
        return parse_yamaha_cl(path)
    return parse_yamaha_cl_binary(path)


def channel_yaml(ch) -> str:
    lines = [f"  - id: {ch.id}"]
    lines.append(f"    name: {ch.name!r}")
    lines.append(f"    hpf_enabled: {str(ch.hpf_enabled).lower()}")
    lines.append(f"    hpf_frequency: {ch.hpf_frequency}")
    if ch.gate and ch.gate.enabled:
        lines.append(f"    gate_enabled: true")
        lines.append(f"    gate_threshold: {ch.gate.threshold}")
    if ch.compressor and ch.compressor.enabled:
        lines.append(f"    compressor_enabled: true")
        lines.append(f"    compressor_threshold: {ch.compressor.threshold}")
        lines.append(f"    compressor_ratio: {ch.compressor.ratio}")
    return "\n".join(lines)


def main():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for sample in sorted(SAMPLES.iterdir()):
        ext = sample.suffix
        if ext not in EXTENSION_PARSER:
            continue
        try:
            show, console = EXTENSION_PARSER[ext](sample)
        except Exception as e:
            print(f"# SKIP {sample.name}: {e}", file=sys.stderr)
            continue

        fixture_path = FIXTURES / f"{sample.name}.yaml"
        if fixture_path.exists():
            print(f"# SKIP {sample.name}: fixture already exists", file=sys.stderr)
            continue

        preview_channels = show.channels[:5]
        yaml_lines = [
            f"# Auto-generated fixture for {sample.name}",
            f"source_console: {console}",
            f"channel_count: {len(show.channels)}",
            "channels:",
        ] + [channel_yaml(ch) for ch in preview_channels]

        yaml_text = "\n".join(yaml_lines) + "\n"
        fixture_path.write_text(yaml_text, encoding="utf-8")
        print(f"wrote {fixture_path.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the generator**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions" && python tools/generate_fixtures.py
```

Expected: prints `wrote <name>.yaml` for each sample file to stderr. Each fixture file is created in `engine/verification/fixtures/`. Any `SKIP` lines mean that sample already has a fixture or the parser errored — investigate errors.

- [ ] **Step 3: Spot-check one fixture**

```bash
cat "engine/verification/fixtures/calibration dynamics full.CLF.yaml"
```

Expected: a YAML file with `channel_count`, `source_console: yamaha_cl`, and `channels` listing a few channels with `gate_threshold` and `compressor_threshold` values.

- [ ] **Step 4: Commit**

```bash
git add tools/generate_fixtures.py engine/verification/fixtures/
git commit -m "feat(fixtures): add fixture generator and baseline YAMLs for all sample files"
```

---

## Task 5: Extend `verify_against_fixture()` and add parametrize test

**Files:**
- Modify: `engine/verification/harness.py` (`verify_against_fixture`)
- Modify: `engine/tests/verification/test_harness.py`

- [ ] **Step 1: Write the failing parametrize test**

Add to `engine/tests/verification/test_harness.py`:

```python
import pytest
from pathlib import Path
from parsers.yamaha_cl_binary import parse_yamaha_cl_binary
from parsers.yamaha_cl import parse_yamaha_cl
from parsers import yamaha_dm7, yamaha_tf, yamaha_rivage
from verification.harness import verify_against_fixture

FIXTURES_DIR = Path(__file__).parent.parent.parent / "verification" / "fixtures"
SAMPLES_DIR = Path(__file__).parent.parent.parent.parent / "samples"

def _all_fixtures():
    if not FIXTURES_DIR.exists():
        return []
    return sorted(FIXTURES_DIR.glob("*.yaml"))

@pytest.mark.parametrize("fixture_path", _all_fixtures(), ids=lambda p: p.stem)
def test_fixture_baseline(fixture_path):
    import yaml

    fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    sample_name = fixture_path.stem  # e.g. "calibration dynamics full.CLF"
    sample_path = SAMPLES_DIR / sample_name
    assert sample_path.exists(), f"Sample file not found: {sample_path}"

    source_console = fixture.get("source_console", "yamaha_cl")
    if source_console == "yamaha_cl":
        with open(sample_path, "rb") as f:
            header = f.read(2)
        show = parse_yamaha_cl(sample_path) if header == b"PK" else parse_yamaha_cl_binary(sample_path)
    elif source_console == "yamaha_dm7":
        show = yamaha_dm7.parse(sample_path.read_bytes())
    elif source_console == "yamaha_tf":
        show = yamaha_tf.parse(str(sample_path))
    elif source_console == "yamaha_rivage_pm":
        show = yamaha_rivage.parse(str(sample_path))
    else:
        pytest.skip(f"No parser registered for {source_console}")

    result = verify_against_fixture(show, sample_name)
    failed = result.failed_checks
    assert not failed, (
        f"Fixture regression for {sample_name}:\n"
        + "\n".join(f"  ch{c.channel_id} {c.parameter}: expected {c.source_value!r}, got {c.target_value!r}"
                    for c in failed)
    )
```

- [ ] **Step 2: Run to confirm tests fail or skip**

```bash
cd engine && python -m pytest tests/verification/test_harness.py::test_fixture_baseline -v
```

Expected: most tests FAIL because `verify_against_fixture()` only checks `channel_count` and `channel_names` — the new YAML fixture fields (`hpf_frequency`, `gate_threshold`, etc.) are not yet checked.

- [ ] **Step 3: Extend `verify_against_fixture()` in `harness.py`**

Inside the `try` block in `verify_against_fixture()`, after the existing `channel_names` block, add:

```python
        if "channels" in fixture:
            ch_by_id = {ch.id: ch for ch in show.channels}
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

                def fx_add(param, expected, actual_val, passed, note=""):
                    result.checks.append(ParameterCheck(
                        channel_id=ch_id,
                        parameter=param,
                        source_value=expected,
                        target_value=actual_val,
                        passed=passed,
                        note=note,
                    ))

                if "name" in fix_ch:
                    fx_add("name", fix_ch["name"], actual.name, fix_ch["name"] == actual.name)
                if "hpf_enabled" in fix_ch:
                    fx_add("hpf_enabled", fix_ch["hpf_enabled"], actual.hpf_enabled,
                           fix_ch["hpf_enabled"] == actual.hpf_enabled)
                if "hpf_frequency" in fix_ch:
                    fx_add("hpf_frequency", fix_ch["hpf_frequency"], actual.hpf_frequency,
                           _floats_equal(fix_ch["hpf_frequency"], actual.hpf_frequency, tol=1.0))
                if "gate_enabled" in fix_ch:
                    gate_enabled = actual.gate is not None and actual.gate.enabled
                    fx_add("gate_enabled", fix_ch["gate_enabled"], gate_enabled,
                           fix_ch["gate_enabled"] == gate_enabled)
                if "gate_threshold" in fix_ch and actual.gate is not None:
                    fx_add("gate_threshold", fix_ch["gate_threshold"], actual.gate.threshold,
                           _floats_equal(fix_ch["gate_threshold"], actual.gate.threshold, tol=0.01))
                if "compressor_enabled" in fix_ch:
                    comp_enabled = actual.compressor is not None and actual.compressor.enabled
                    fx_add("compressor_enabled", fix_ch["compressor_enabled"], comp_enabled,
                           fix_ch["compressor_enabled"] == comp_enabled)
                if "compressor_threshold" in fix_ch and actual.compressor is not None:
                    fx_add("compressor_threshold", fix_ch["compressor_threshold"],
                           actual.compressor.threshold,
                           _floats_equal(fix_ch["compressor_threshold"], actual.compressor.threshold, tol=0.01))
                if "compressor_ratio" in fix_ch and actual.compressor is not None:
                    fx_add("compressor_ratio", fix_ch["compressor_ratio"],
                           actual.compressor.ratio,
                           _floats_equal(fix_ch["compressor_ratio"], actual.compressor.ratio, tol=0.01))
```

- [ ] **Step 4: Run the parametrize test**

```bash
cd engine && python -m pytest tests/verification/test_harness.py::test_fixture_baseline -v
```

Expected: all fixture tests PASS (the YAMLs were generated from the parsers, so they match). If any fail, the fixture was generated incorrectly — delete that fixture, re-run the generator for just that file, and recommit.

- [ ] **Step 5: Run full suite**

```bash
cd engine && python -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add engine/verification/harness.py engine/tests/verification/test_harness.py
git commit -m "feat(harness): extend verify_against_fixture with HPF/gate/comp checks; add parametrize fixture suite"
```

---

## Task 6: Yamaha QL parser

**Files:**
- Create: `engine/parsers/yamaha_ql.py`
- Modify: `engine/translator.py`
- Modify: `engine/verification/harness.py` (`_parser_for`)
- Test: `engine/tests/test_yamaha_ql_parser.py`

- [ ] **Step 1: Write failing test**

Create `engine/tests/test_yamaha_ql_parser.py`:

```python
"""Tests for the Yamaha QL parser.

The QL binary format is identical to CL. The parser is a thin wrapper that
sets source_console to "yamaha_ql". We test using existing CL sample files
since the binary structure is the same — a real QL sample confirms channel
count differences when available.
"""
import pytest
from pathlib import Path
from parsers.yamaha_ql import parse_yamaha_ql

SAMPLES = Path(__file__).parent.parent.parent / "samples"

def test_parse_yamaha_ql_returns_showfile_with_yamaha_ql_console():
    sample = SAMPLES / "calibration file.CLF"
    show = parse_yamaha_ql(sample)
    assert show.source_console == "yamaha_ql"

def test_parse_yamaha_ql_channels_parsed():
    sample = SAMPLES / "calibration file.CLF"
    show = parse_yamaha_ql(sample)
    assert len(show.channels) > 0

def test_parse_yamaha_ql_hpf_present():
    sample = SAMPLES / "calibration file.CLF"
    show = parse_yamaha_ql(sample)
    # At least one channel should have HPF data
    assert any(ch.hpf_frequency > 0 for ch in show.channels)
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd engine && python -m pytest tests/test_yamaha_ql_parser.py -v
```

Expected: `FAILED` — `parsers.yamaha_ql` does not exist.

- [ ] **Step 3: Create `engine/parsers/yamaha_ql.py`**

```python
"""Yamaha QL series parser.

The QL binary format (.CLF / .CLE) is structurally identical to the CL
series format — same MBDF structure, same parameter offsets. This parser
is a thin wrapper over parse_yamaha_cl_binary that tags the result with
source_console="yamaha_ql" so the translator can distinguish QL files.

Channel counts differ by model:
  QL5: 64 input channels
  QL1: 32 input channels
The binary parser handles both transparently via record-count detection.
"""
from pathlib import Path

from models.universal import ShowFile
from parsers.yamaha_cl_binary import parse_yamaha_cl_binary


def parse_yamaha_ql(filepath: Path) -> ShowFile:
    show = parse_yamaha_cl_binary(filepath)
    show.source_console = "yamaha_ql"
    return show
```

- [ ] **Step 4: Run tests**

```bash
cd engine && python -m pytest tests/test_yamaha_ql_parser.py -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Register in `translator.py`**

In `translator.py`, after the existing `_tf_parser` import, add:

```python
from parsers.yamaha_ql import parse_yamaha_ql
```

In `PARSERS`, add:

```python
    "yamaha_ql": parse_yamaha_ql,
```

In `WRITERS`, add (QL files use the same binary writer as CL until a QL template is sourced):

```python
    "yamaha_ql": write_yamaha_cl_binary,
```

- [ ] **Step 6: Register in `harness._parser_for()`**

In `harness.py`, inside `_parser_for()`, add before the `raise ValueError`:

```python
    if target_format == "yamaha_ql":
        from parsers.yamaha_ql import parse_yamaha_ql
        return parse_yamaha_ql
```

- [ ] **Step 7: Verify translator accepts yamaha_ql as source**

```bash
cd engine && python -c "
from pathlib import Path
from translator import translate
result = translate(Path('../samples/calibration file.CLF'), 'yamaha_ql', 'digico_sd')
print(f'channels: {result.channel_count}')
print(f'parse_gate_passed: {result.parse_gate_passed}')
print(f'overall fidelity: {result.fidelity_score.overall:.1f}%')
"
```

Expected: prints channel count, `parse_gate_passed: True`, and a fidelity score.

- [ ] **Step 8: Run full suite**

```bash
cd engine && python -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add engine/parsers/yamaha_ql.py engine/translator.py engine/verification/harness.py engine/tests/test_yamaha_ql_parser.py
git commit -m "feat(parser): add Yamaha QL parser — thin wrapper over CL binary; register in translator + harness"
```

---

## Task 7: A&H dLive skeleton (stubs to unblock console registration)

**Files:**
- Create: `engine/parsers/ah_dlive.py`
- Create: `engine/writers/ah_dlive.py`
- Modify: `engine/translator.py`
- Test: `engine/tests/test_ah_dlive.py`

- [ ] **Step 1: Write failing test**

Create `engine/tests/test_ah_dlive.py`:

```python
"""Tests for A&H dLive parser/writer stubs.

These tests verify that the stubs are registered and raise NotImplementedError
(not ImportError or AttributeError) — so the rest of the system knows they
exist and what's blocking them.
"""
import pytest
from pathlib import Path
from parsers.ah_dlive import parse_ah_dlive
from writers.ah_dlive import write_ah_dlive
from translator import PARSERS, WRITERS, translate, UnsupportedConsolePair

def test_ah_dlive_parser_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="pending calibration"):
        parse_ah_dlive(Path("dummy.AHsession"))

def test_ah_dlive_writer_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="pending calibration"):
        write_ah_dlive(None)

def test_ah_dlive_registered_in_parsers():
    assert "ah_dlive" in PARSERS

def test_ah_dlive_registered_in_writers():
    assert "ah_dlive" in WRITERS
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd engine && python -m pytest tests/test_ah_dlive.py -v
```

Expected: `FAILED` — modules don't exist yet.

- [ ] **Step 3: Create `engine/parsers/ah_dlive.py`**

```python
"""A&H dLive parser — PENDING CALIBRATION.

dLive show files (.AHsession) are ZIP archives containing XML documents.
Parsing approach will use xml.etree.ElementTree, the same as the DiGiCo
and Yamaha CL XML parsers.

This stub is registered in translator.PARSERS so the console appears in
the supported list and the UI can display it as "coming soon". It raises
NotImplementedError until a real .AHsession sample file is available.

Unblocking steps:
  1. Install dLive Director from allen-heath.com
  2. Create a show with ~10 named channels, HPF on, one gate, one compressor
  3. Save as .AHsession and drop in samples/
  4. Run tools/ah_dlive_probe.py to discover XML field paths
  5. Implement this parser following the pattern in parsers/digico_sd.py
"""
from pathlib import Path
from models.universal import ShowFile


def parse_ah_dlive(filepath: Path) -> ShowFile:
    raise NotImplementedError(
        "A&H dLive parser pending calibration against .AHsession sample file. "
        "See engine/parsers/ah_dlive.py docstring for unblocking steps."
    )
```

- [ ] **Step 4: Create `engine/writers/ah_dlive.py`**

```python
"""A&H dLive writer — PENDING CALIBRATION.

Generates a .AHsession ZIP archive from a universal ShowFile.
Approach: build XML tree using ElementTree, zip into the session
folder structure that dLive Director expects.

Blocked on the same .AHsession sample file as the parser — the ZIP
structure and XML schema must be confirmed from a real file before
this can write valid output.
"""
from models.universal import ShowFile


def write_ah_dlive(show: ShowFile) -> bytes:
    raise NotImplementedError(
        "A&H dLive writer pending calibration against .AHsession sample file. "
        "See engine/writers/ah_dlive.py docstring for unblocking steps."
    )
```

- [ ] **Step 5: Register in `translator.py`**

Add imports after the existing writer imports:

```python
from parsers.ah_dlive import parse_ah_dlive
from writers.ah_dlive import write_ah_dlive
```

Add to `PARSERS`:

```python
    "ah_dlive": parse_ah_dlive,
```

Add to `WRITERS`:

```python
    "ah_dlive": write_ah_dlive,
```

- [ ] **Step 6: Run tests**

```bash
cd engine && python -m pytest tests/test_ah_dlive.py -v
```

Expected: 4 PASSED.

- [ ] **Step 7: Verify translate() raises UnsupportedConsolePair when ah_dlive is source (parse blocked), not a crash**

```bash
cd engine && python -c "
from pathlib import Path
from translator import translate
try:
    translate(Path('dummy.AHsession'), 'ah_dlive', 'yamaha_cl_binary')
except NotImplementedError as e:
    print(f'NotImplementedError (expected): {e}')
except Exception as e:
    print(f'UNEXPECTED: {type(e).__name__}: {e}')
"
```

Expected: `NotImplementedError (expected): A&H dLive parser pending calibration...`

- [ ] **Step 8: Run full suite**

```bash
cd engine && python -m pytest tests/ -q
```

Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add engine/parsers/ah_dlive.py engine/writers/ah_dlive.py engine/translator.py engine/tests/test_ah_dlive.py
git commit -m "feat(parser): add A&H dLive stubs — registered in translator, NotImplementedError pending sample file"
```

---

## Final Verification

- [ ] **Run the full test suite one last time**

```bash
cd engine && python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

Expected: all tests pass. Count should be 202 (existing) + new tests from this sprint.

- [ ] **Smoke-test fidelity score end-to-end**

```bash
cd engine && python -c "
from pathlib import Path
from translator import translate

result = translate(
    Path('../samples/calibration dynamics full.CLF'),
    'yamaha_cl',
    'yamaha_cl_binary'
)
s = result.fidelity_score
print(f'parse_gate_passed: {result.parse_gate_passed}')
print(f'names:      {s.names:.1f}%')
print(f'hpf:        {s.hpf:.1f}%')
print(f'eq:         {s.eq:.1f}%')
print(f'gate:       {s.gate:.1f}%')
print(f'compressor: {s.compressor:.1f}%')
print(f'overall:    {s.overall:.1f}%')
"
```

Expected: all scores print without error. `parse_gate_passed: True`. Scores are realistic (likely 90–100% for well-supported params).

- [ ] **Final commit if any loose files**

```bash
cd "c:/Users/grego/Documents/Jobing/Claude Code/AudioSolutions" && git status
```

Commit any uncommitted changes with an appropriate message.
