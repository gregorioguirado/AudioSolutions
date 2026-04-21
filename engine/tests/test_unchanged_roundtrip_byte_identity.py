"""Regression test: parse(template) -> write(showfile) -> output bytes must
produce decompressed inner blobs that are byte-identical to the template's
decompressed inner blobs.

This catches the exact class of bug the user hit: writer "succeeds" and our
parser re-reads it cleanly, but the output is actually corrupting bytes in
non-channel regions of the file. The Yamaha Editor apps then reject the
file because those corrupted bytes belong to other sections (scene data,
matrices, mixer metadata).

For each writable binary target we:
  1. Parse the writer's own template into a ShowFile.
  2. Write that ShowFile back out.
  3. Extract every zlib blob from both template and output.
  4. Assert each decompressed blob matches byte-for-byte.

Writer fidelity to an *unchanged* ShowFile is the floor: anything less
means we're overwriting bytes we don't own.
"""
from __future__ import annotations

import sys
import zlib
from pathlib import Path

import pytest

ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))


def _all_blobs(data: bytes) -> list[tuple[int, bytes]]:
    """Return (offset, decompressed_bytes) for every substantial zlib blob."""
    blobs: list[tuple[int, bytes]] = []
    i = 0
    while i < len(data) - 1:
        if data[i] == 0x78 and data[i + 1] in (0x01, 0x5E, 0x9C, 0xDA):
            try:
                d = zlib.decompressobj()
                dec = d.decompress(data[i:])
                if len(dec) > 100:
                    blobs.append((i, dec))
                    # Skip past this blob to avoid catching overlapping starts
                    i += len(data) - i - len(d.unused_data)
                    continue
            except zlib.error:
                pass
        i += 1
    return blobs


@pytest.mark.parametrize(
    ("template_name", "parser_import", "writer_import", "parser_takes_bytes"),
    [
        ("tf_empty.tff",           "parsers.yamaha_tf:parse",         "writers.yamaha_tf:write_yamaha_tf",           False),
        ("rivage_empty.RIVAGEPM",  "parsers.yamaha_rivage:parse",     "writers.yamaha_rivage:write_yamaha_rivage",   False),
        ("dm7_empty.dm7f",         "parsers.yamaha_dm7:parse",        "writers.yamaha_dm7:write_yamaha_dm7",         True),
    ],
)
def test_unchanged_roundtrip_preserves_all_template_blobs(
    template_name, parser_import, writer_import, parser_takes_bytes,
):
    """Write(Parse(template)) must not disturb any template blob's content.

    The file's total byte-length may differ (recompression changes compressed
    sizes) but each decompressed blob must be identical.
    """
    tmpl_path = ENGINE_DIR / "writers" / "templates" / template_name
    tmpl_bytes = tmpl_path.read_bytes()

    # Dynamic import of parser and writer
    p_module, p_func = parser_import.split(":")
    w_module, w_func = writer_import.split(":")
    parser_mod = __import__(p_module, fromlist=[p_func])
    writer_mod = __import__(w_module, fromlist=[w_func])
    parse = getattr(parser_mod, p_func)
    write = getattr(writer_mod, w_func)

    # Parse -> Write
    sh = parse(tmpl_bytes) if parser_takes_bytes else parse(str(tmpl_path))
    out_bytes = write(sh)

    # Blob-by-blob comparison
    blobs_t = _all_blobs(tmpl_bytes)
    blobs_o = _all_blobs(out_bytes)

    assert len(blobs_o) == len(blobs_t), (
        f"{template_name}: blob count changed: template={len(blobs_t)} output={len(blobs_o)}"
    )
    for idx, ((_, dec_t), (_, dec_o)) in enumerate(zip(blobs_t, blobs_o)):
        assert dec_t == dec_o, (
            f"{template_name}: blob {idx} content diverged "
            f"(template={len(dec_t)} bytes, output={len(dec_o)} bytes). "
            f"Writer is overwriting template bytes it shouldn't touch — "
            f"the Yamaha Editor will reject this file."
        )


def test_cl_binary_unchanged_roundtrip_is_byte_identical():
    """CL binary (.CLF) is a flat, uncompressed binary.

    Unlike TF/RIVAGE/DM7 which wrap their data in zlib blobs, the CL binary
    format is laid out as raw bytes. The writer must produce a file that is
    EXACTLY the template bytes when given an unchanged ShowFile, otherwise
    the real Yamaha Console Editor rejects with errors like
    "different kinds of data! (-7)" because packed flag bytes and non-channel
    regions get corrupted.

    The correction_map inside writers/yamaha_cl_binary.py is what makes this
    pass. If you change the writer, this test must still pass.
    """
    from parsers.yamaha_cl_binary import parse_yamaha_cl_binary
    from writers.yamaha_cl_binary import write_yamaha_cl_binary

    tmpl_path = ENGINE_DIR / "writers" / "templates" / "cl5_empty.CLF"
    tmpl_bytes = tmpl_path.read_bytes()

    sh = parse_yamaha_cl_binary(tmpl_path)
    out_bytes = write_yamaha_cl_binary(sh)

    assert len(out_bytes) == len(tmpl_bytes), (
        f"output length changed: template={len(tmpl_bytes)} output={len(out_bytes)}"
    )
    if tmpl_bytes != out_bytes:
        diffs = [i for i in range(len(tmpl_bytes)) if tmpl_bytes[i] != out_bytes[i]]
        sample = diffs[:10]
        raise AssertionError(
            f"CL binary unchanged round-trip is not byte-identical. "
            f"{len(diffs)} bytes differ, first 10 offsets: {sample}. "
            f"The writer's correction map is missing or broken; "
            f"the real CL editor will reject this file."
        )
