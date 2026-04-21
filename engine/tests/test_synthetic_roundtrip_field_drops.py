"""Synthetic-ShowFile round-trip tests that expose silent field drops.

The harness fidelity score can lie: if a parser doesn't extract a field
(e.g. mix_bus_assignments on a binary Yamaha parser), the universal
ShowFile has an empty list. The writer writes what it gets (nothing).
The re-parse also reads nothing. "Source matches target" = 100%.

These tests sidestep the parser by constructing a ShowFile in Python
with known-rich data, running write→re-parse, then asserting fields
survive. Any field loss is surfaced as an xfail-marked test (so the
failure is documented but doesn't break CI) with a clear message about
the writer-level gap.

Use this list to prioritise which writers to enrich next.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from models.universal import Channel, ChannelColor, ShowFile  # noqa: E402
from translator import WRITERS  # noqa: E402
from verification.harness import _parser_for  # noqa: E402


_SUFFIX_FOR = {
    "digico_sd": ".show",
    "yamaha_cl": ".cle",
    "yamaha_cl_binary": ".CLF",
    "yamaha_ql": ".CLF",
    "yamaha_tf": ".tff",
    "yamaha_dm7": ".dm7f",
    "yamaha_rivage": ".RIVAGEPM",
}


def _roundtrip_via_writer(show: ShowFile, target: str) -> Channel | None:
    writer = WRITERS[target]
    out = writer(show)
    with tempfile.NamedTemporaryFile(suffix=_SUFFIX_FOR[target], delete=False) as f:
        f.write(out)
        tmp = Path(f.name)
    try:
        parsed = _parser_for(target)(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    return parsed.channels[0] if parsed.channels else None


@pytest.mark.parametrize("target", [
    "yamaha_cl_binary", "yamaha_ql", "yamaha_tf",
    "yamaha_dm7", "yamaha_rivage", "yamaha_cl", "digico_sd",
])
def test_name_survives_writer(target):
    """Channel name must round-trip through every writer."""
    src = Channel(id=1, name="KICK_IN", color=ChannelColor.RED,
                  input_patch=1, hpf_frequency=80.0, hpf_enabled=False)
    show = ShowFile(source_console="test", channels=[src])
    tgt = _roundtrip_via_writer(show, target)
    assert tgt is not None, f"{target}: no channels parsed back"
    assert tgt.name == "KICK_IN", f"{target}: name {tgt.name!r} != {src.name!r}"


# Writers with known mix-bus gaps — xfail so the failure is documented
# but the suite still passes. When a writer is enriched to round-trip
# mix buses, remove it from this list.
_MIX_BUS_GAPS = {"yamaha_cl_binary", "yamaha_ql", "yamaha_tf", "yamaha_dm7", "yamaha_rivage"}


@pytest.mark.parametrize("target", [
    "yamaha_cl_binary", "yamaha_ql", "yamaha_tf",
    "yamaha_dm7", "yamaha_rivage", "yamaha_cl", "digico_sd",
])
def test_mix_bus_assignments_survive_writer(target, request):
    """Mix bus assignments should round-trip. Fails today on every
    binary Yamaha writer — silent field drop, see _MIX_BUS_GAPS."""
    if target in _MIX_BUS_GAPS:
        request.node.add_marker(
            pytest.mark.xfail(reason=f"{target} writer drops mix_bus_assignments")
        )
    src = Channel(id=1, name="T", color=ChannelColor.RED,
                  input_patch=1, hpf_frequency=80.0, hpf_enabled=False,
                  mix_bus_assignments=[1, 3, 5, 7])
    show = ShowFile(source_console="test", channels=[src])
    tgt = _roundtrip_via_writer(show, target)
    assert tgt is not None
    assert sorted(tgt.mix_bus_assignments) == [1, 3, 5, 7], (
        f"{target}: mix_bus_assignments = {sorted(tgt.mix_bus_assignments)} != [1,3,5,7]"
    )


# Writers that don't preserve VCA assignments today
_VCA_GAPS = {"yamaha_tf", "yamaha_rivage"}


@pytest.mark.parametrize("target", [
    "yamaha_cl_binary", "yamaha_ql", "yamaha_tf",
    "yamaha_dm7", "yamaha_rivage", "yamaha_cl", "digico_sd",
])
def test_vca_assignments_survive_writer(target, request):
    """VCA/DCA assignments should round-trip. Fails today on TF and RIVAGE."""
    if target in _VCA_GAPS:
        request.node.add_marker(
            pytest.mark.xfail(reason=f"{target} writer drops vca_assignments")
        )
    src = Channel(id=1, name="T", color=ChannelColor.RED,
                  input_patch=1, hpf_frequency=80.0, hpf_enabled=False,
                  vca_assignments=[1, 2, 4])
    show = ShowFile(source_console="test", channels=[src])
    tgt = _roundtrip_via_writer(show, target)
    assert tgt is not None
    assert sorted(tgt.vca_assignments) == [1, 2, 4], (
        f"{target}: vca_assignments = {sorted(tgt.vca_assignments)} != [1,2,4]"
    )
