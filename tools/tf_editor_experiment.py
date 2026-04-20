"""Narrows the TF Editor rejection bug in ONE user test round.

Produces 5 candidate .tff files, each a minimally-different modification
of DOM CASMURRO 2.tff (a known editor-accepted file). User opens each
in TF Editor and reports which PASS and which FAIL. The pattern
identifies the exact class of modification the editor rejects.

    python tools/tf_editor_experiment.py

Creates files under .tmp/tf_experiments/ and prints a checklist.
"""
from __future__ import annotations

import shutil
import struct
import sys
import uuid
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "samples" / "DOM CASMURRO 2.tff"
OUT_DIR = REPO / ".tmp" / "tf_experiments"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _find_first_zlib(data: bytes) -> int:
    for i in range(40, 2000):
        if data[i] == 0x78 and data[i + 1] in (0x01, 0x5E, 0x9C, 0xDA):
            try:
                zlib.decompressobj().decompress(data[i:])
                return i
            except zlib.error:
                pass
    raise ValueError("no zlib blob found")


def _recompress_first_blob(data: bytes) -> bytes:
    """Decompress the first zlib blob then re-compress at level 1, splice back.
    Tests whether the editor's acceptance depends on the exact compressed
    byte stream (vs only the decompressed payload)."""
    start = _find_first_zlib(data)
    d = zlib.decompressobj()
    inner = d.decompress(data[start:])
    trailing = d.unused_data
    new_blob = zlib.compress(inner, level=1)
    return data[:start] + new_blob + trailing


def _change_uuid(data: bytes) -> bytes:
    buf = bytearray(data)
    buf[0x38:0x48] = uuid.uuid4().bytes
    return bytes(buf)


def _rename_ch1_via_writer(data: bytes) -> bytes:
    """Use our TF writer to rename channel 1 to 'EXPT1'. This tests whether
    in-blob modifications through our writer trigger rejection, above and
    beyond the UUID + recompression changes."""
    # We can't use the translator-level function easily here (it takes a path
    # and console name). Instead, parse the file in-place, rename, write back.
    sys.path.insert(0, str(REPO / "engine"))
    from parsers.yamaha_tf import parse  # noqa: E402
    from writers.yamaha_tf import write_yamaha_tf  # noqa: E402
    # Write source to a temp, parse, modify, write back to bytes
    tmp = OUT_DIR / "_tmp_source.tff"
    tmp.write_bytes(data)
    show = parse(str(tmp))
    if show.channels:
        show.channels[0].name = "EXPT1"
    out = write_yamaha_tf(show)
    tmp.unlink(missing_ok=True)
    return out


def _rename_ch1_via_byte_patch(data: bytes) -> bytes:
    """Rename channel 1 INSIDE the first zlib blob by decompressing, patching
    the name at the known channel-record offset (16 bytes into record 0),
    re-compressing. This isolates "can we modify channel data at all" from
    "does our writer do something else the editor doesn't like"."""
    start = _find_first_zlib(data)
    d = zlib.decompressobj()
    inner = bytearray(d.decompress(data[start:]))
    trailing = d.unused_data
    # Find MMSXLIT magic + schema_size to locate channel record 0
    mms = inner.index(b"MMSXLIT\x00")
    schema_size = struct.unpack_from("<I", inner, mms + 80)[0]
    data_start = mms + 88 + schema_size
    # Record 0 name at offset +16, 64 bytes
    name_off = data_start + 16
    new_name = b"EXPT1" + b"\x00" * (64 - 5)
    inner[name_off : name_off + 64] = new_name
    new_blob = zlib.compress(bytes(inner), level=1)
    return data[:start] + new_blob + trailing


def main() -> None:
    if not SRC.exists():
        print(f"ERROR: source not found: {SRC}")
        sys.exit(2)
    src_bytes = SRC.read_bytes()

    experiments = [
        (
            "01_exact_copy.tff",
            "Exact byte-for-byte copy. MUST pass — sanity check that Editor can open this file in this location.",
            lambda: src_bytes,
        ),
        (
            "02_only_uuid_changed.tff",
            "Only the 16 bytes at 0x38 changed to a fresh UUID. Tests whether the UUID is bound to content.",
            lambda: _change_uuid(src_bytes),
        ),
        (
            "03_only_recompress.tff",
            "First zlib blob decompressed+recompressed at same level 1, no content change. Tests whether Editor accepts rewritten compressed bytes.",
            lambda: _recompress_first_blob(src_bytes),
        ),
        (
            "04_rename_ch1_bytepatch.tff",
            "Channel 1 name byte-patched to 'EXPT1' in-blob, UUID unchanged. Tests whether any in-blob change triggers rejection.",
            lambda: _rename_ch1_via_byte_patch(src_bytes),
        ),
        (
            "05_rename_ch1_via_writer.tff",
            "Channel 1 renamed to 'EXPT1' via our yamaha_tf writer. This is what v0.3.10 would produce for a minimal edit.",
            lambda: _rename_ch1_via_writer(src_bytes),
        ),
    ]

    for filename, desc, produce in experiments:
        try:
            out = produce()
        except Exception as e:  # noqa: BLE001
            print(f"[SKIP] {filename}: could not produce ({type(e).__name__}: {e})")
            continue
        path = OUT_DIR / filename
        path.write_bytes(out)
        print(f"[OK]   {filename}  ({len(out)} bytes)")

    print()
    print("=" * 72)
    print("MANUAL TEST INSTRUCTIONS")
    print("=" * 72)
    print(f"Files are in: {OUT_DIR}")
    print()
    for filename, desc, _ in experiments:
        print(f"  [ ] {filename}")
        print(f"      {desc}")
        print(f"      -> Opens cleanly in TF Editor? yes / no / partial")
        print()
    print("Report which are [x] yes and which are [ ] no back to me.")
    print("The pattern tells us exactly what the editor is validating.")


if __name__ == "__main__":
    main()
