"""Regression tests for Yamaha Editor app compatibility.

TF Editor / RIVAGE PM Editor / DM7 Editor all accept files that our
*parser* reads cleanly but reject files that deviate from the real
Editor's byte-layout — even when the decompressed content is byte-for-byte
identical. Failure mode: Editor opens the file, shows "format not
recognised", nothing else.

These tests catch regressions where:
  - Our writer recompresses the inner MBDF blob at a different zlib
    level than the Editor uses (level 1, i.e. header ``78 01``).
  - The outer header (up to the compressed blob) ever diverges from the
    template's outer header. That header holds format identifiers and a
    16-byte integrity field at offset 0x38 that we MUST preserve verbatim.

These are purely structural checks; fidelity of the payload is covered
separately by ``test_all_routes.py`` and per-writer round-trip tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from translator import translate  # noqa: E402

SAMPLES_DIR = ENGINE_DIR.parent / "samples"
TEMPLATES_DIR = ENGINE_DIR / "writers" / "templates"


def _find_zlib_offset(data: bytes) -> int:
    """Locate the first zlib header byte pair in a file."""
    for i in range(len(data) - 1):
        if data[i] == 0x78 and data[i + 1] in (0x01, 0x5E, 0x9C, 0xDA):
            return i
    raise ValueError("no zlib header found")


@pytest.mark.parametrize(
    ("source_sample", "source_console", "target_console", "template_name"),
    [
        ("dm7_named.dm7f",                  "yamaha_dm7",    "yamaha_tf",     "tf_empty.tff"),
        ("rivage_hpf_calib.RIVAGEPM",       "yamaha_rivage", "yamaha_tf",     "tf_empty.tff"),
        ("Example 1 CL5.CLE",               "yamaha_cl",     "yamaha_rivage", "rivage_empty.RIVAGEPM"),
        ("dm7_named.dm7f",                  "yamaha_dm7",    "yamaha_rivage", "rivage_empty.RIVAGEPM"),
        ("rivage_empty.RIVAGEPM",           "yamaha_rivage", "yamaha_dm7",    "dm7_empty.dm7f"),
        ("DOM CASMURRO 2.tff",              "yamaha_tf",     "yamaha_dm7",    "dm7_empty.dm7f"),
    ],
)
def test_writer_output_preserves_editor_outer_header(
    source_sample, source_console, target_console, template_name,
):
    """The bytes before the zlib blob must match the template verbatim.

    Editor integrity fields live in this region. Any deviation = the
    Editor rejects the file.
    """
    src = SAMPLES_DIR / source_sample
    tmpl = (TEMPLATES_DIR / template_name).read_bytes()

    result = translate(src, source_console, target_console)
    ours = result.output_bytes

    z_tmpl = _find_zlib_offset(tmpl)
    z_ours = _find_zlib_offset(ours)

    assert z_ours == z_tmpl, (
        f"{target_console}: zlib blob starts at offset {z_ours} in output but "
        f"{z_tmpl} in template — outer header shifted"
    )
    # Outer-header bytes must match EXCEPT at offset 0x38..0x47 which is a
    # per-save UUID that the Editor expects to be regenerated fresh every
    # write. See engine/writers/yamaha_dm7.py for the forensic diff that
    # confirmed this across the Yamaha MBDF family.
    _UUID_OFFSET, _UUID_LEN = 0x38, 16
    ours_masked = ours[:_UUID_OFFSET] + b"\x00" * _UUID_LEN + ours[_UUID_OFFSET + _UUID_LEN:z_tmpl]
    tmpl_masked = tmpl[:_UUID_OFFSET] + b"\x00" * _UUID_LEN + tmpl[_UUID_OFFSET + _UUID_LEN:z_tmpl]
    assert ours_masked == tmpl_masked, (
        f"{target_console}: outer header bytes (before compressed blob) "
        f"differ from template OUTSIDE the UUID region — Editor integrity "
        f"fields will fail"
    )
    # And the UUID MUST have been regenerated (non-zero and != template).
    assert ours[_UUID_OFFSET:_UUID_OFFSET + _UUID_LEN] != b"\x00" * _UUID_LEN, (
        f"{target_console}: UUID slot at 0x38 is all zeros — writer failed to "
        f"generate a fresh UUID"
    )
    assert ours[_UUID_OFFSET:_UUID_OFFSET + _UUID_LEN] != tmpl[_UUID_OFFSET:_UUID_OFFSET + _UUID_LEN], (
        f"{target_console}: UUID at 0x38 is the template's value — writer did "
        f"not regenerate it, Editor will reject"
    )


@pytest.mark.parametrize(
    ("source_sample", "source_console", "target_console"),
    [
        ("dm7_named.dm7f",            "yamaha_dm7",    "yamaha_tf"),
        ("rivage_hpf_calib.RIVAGEPM", "yamaha_rivage", "yamaha_tf"),
        ("Example 1 CL5.CLE",         "yamaha_cl",     "yamaha_rivage"),
        ("dm7_named.dm7f",            "yamaha_dm7",    "yamaha_rivage"),
        ("rivage_empty.RIVAGEPM",     "yamaha_rivage", "yamaha_dm7"),
        ("DOM CASMURRO 2.tff",        "yamaha_tf",     "yamaha_dm7"),
    ],
)
def test_writer_output_uses_zlib_level_1(
    source_sample, source_console, target_console,
):
    """Yamaha Editor apps only accept zlib level-1 compressed blobs.

    Level-1 blobs start with the magic byte pair ``78 01``. Other levels
    (``78 9C`` for level 6, ``78 DA`` for level 9) produce valid zlib
    output that our own parser reads but the Editor refuses.
    """
    result = translate(SAMPLES_DIR / source_sample, source_console, target_console)
    ours = result.output_bytes
    z = _find_zlib_offset(ours)
    level_byte = ours[z + 1]
    assert level_byte == 0x01, (
        f"{target_console}: zlib level byte at offset {z+1} is 0x{level_byte:02x} "
        f"(expected 0x01). Yamaha Editor will reject this file."
    )
