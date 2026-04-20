"""Round 2 — the zlib recompression breaks the file (round 1: 03 failed).
Two new questions to answer with one test round:

1. Does the editor check the compressed BYTE STREAM, or does it check a
   size/length/checksum field elsewhere in the outer header that we'd
   need to update?
2. Can we modify the file at all without breaking it — specifically via
   a byte-substitution inside the compressed stream that preserves the
   stream's length?

Candidates produced (all based on samples/DOM CASMURRO 2.tff):

  11 — exact copy (sanity)
  12 — recompress at level 1, then zero out bytes 0x80..0x8f in the
       outer header (after the UUID). If this still fails = editor
       uses content elsewhere in header for validation.
  13 — recompress at level 9 (zlib max). Shorter file. If this and
       03 both fail but 12 also fails = validation not about size.
  14 — recompress using zlib.compressobj with a fixed strategy and
       memory level to match what the editor might use. Last-ditch
       attempt to reproduce byte-identical compressed output.
  15 — in the SOURCE file's compressed stream, flip one literal byte
       inside the zlib stream (NOT recompress — direct byte overwrite,
       which corrupts the stream but doesn't change its length). If
       this fails in a different way (e.g. "corrupted" not "couldn't
       access") = zlib integrity check.
  16 — truncate the last 8 bytes of the file. Tests whether there's
       an appended trailer (checksum / end marker) the editor reads.
"""
from __future__ import annotations

import struct
import sys
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


def recompress(data: bytes, level: int = 1) -> bytes:
    start = _find_first_zlib(data)
    d = zlib.decompressobj()
    inner = d.decompress(data[start:])
    trailing = d.unused_data
    new_blob = zlib.compress(inner, level=level)
    return data[:start] + new_blob + trailing


def zero_outer_range(data: bytes, start: int, end: int) -> bytes:
    buf = bytearray(data)
    buf[start:end] = b"\x00" * (end - start)
    return bytes(buf)


def recompress_max_compatibility(data: bytes) -> bytes:
    """Try to reproduce the editor's exact compression by matching zlib
    defaults more aggressively. Python's zlib.compress uses wbits=15,
    memLevel=8 by default at level 1. Some Yamaha tools use memLevel=9
    (max) or different strategy — test Z_DEFAULT_STRATEGY with max mem."""
    start = _find_first_zlib(data)
    d = zlib.decompressobj()
    inner = d.decompress(data[start:])
    trailing = d.unused_data
    compressor = zlib.compressobj(
        level=1,
        method=zlib.DEFLATED,
        wbits=15,
        memLevel=9,
        strategy=zlib.Z_DEFAULT_STRATEGY,
    )
    new_blob = compressor.compress(inner) + compressor.flush(zlib.Z_FINISH)
    return data[:start] + new_blob + trailing


def flip_one_compressed_byte(data: bytes) -> bytes:
    """Flip a single byte DEEP inside the zlib stream (not near start/end
    so it won't affect the stream header or adler32 checksum). Tests
    whether the editor does zlib integrity checking."""
    start = _find_first_zlib(data)
    # Flip byte 200 into the compressed stream (well past the 2-byte header)
    target = start + 200
    buf = bytearray(data)
    buf[target] ^= 0x55  # flip some bits
    return bytes(buf)


def truncate_trailer(data: bytes, trim: int = 8) -> bytes:
    return data[:-trim]


def main() -> None:
    if not SRC.exists():
        print(f"ERROR: {SRC} missing")
        sys.exit(2)
    src = SRC.read_bytes()

    experiments = [
        ("11_exact_copy.tff", "Sanity — identical to source", lambda: src),
        (
            "12_recompress_then_zero_outer_80_8f.tff",
            "Recompress + zero 16 bytes of outer header AFTER the UUID "
            "(0x80..0x8f). If this fails alongside 03, we know the editor "
            "doesn't use those bytes as a checksum seed.",
            lambda: zero_outer_range(recompress(src, 1), 0x80, 0x90),
        ),
        (
            "13_recompress_level_9.tff",
            "Recompress at max (level 9). Shorter blob than level 1. Tests "
            "whether rejection depends on blob size or on byte-identity.",
            lambda: recompress(src, 9),
        ),
        (
            "14_recompress_memlevel_9.tff",
            "Recompress level 1 with memLevel=9 (may match Yamaha's choice).",
            lambda: recompress_max_compatibility(src),
        ),
        (
            "15_flip_one_compressed_byte.tff",
            "Flip a single byte deep in the zlib stream. If Editor opens "
            "cleanly, it doesn't verify zlib integrity. If it gives a "
            "DIFFERENT error than 'couldn't access' (e.g. 'corrupted') we "
            "know the integrity check is at zlib level.",
            lambda: flip_one_compressed_byte(src),
        ),
        (
            "16_truncate_last_8_bytes.tff",
            "Remove the last 8 bytes of the file. If the file opens, there's "
            "no trailing checksum/marker. If it fails, there's a trailer.",
            lambda: truncate_trailer(src, 8),
        ),
    ]

    for fname, desc, produce in experiments:
        try:
            out = produce()
        except Exception as e:  # noqa: BLE001
            print(f"[SKIP] {fname}: {type(e).__name__}: {e}")
            continue
        (OUT_DIR / fname).write_bytes(out)
        print(f"[OK]   {fname}  ({len(out)} bytes)")

    print()
    print("=" * 72)
    print("Open each in TF Editor and report yes/no (and note the exact error")
    print("text if 'no' so we can see if it's 'couldn't access' or something")
    print("different like 'corrupted'):")
    print("=" * 72)
    for fname, desc, _ in experiments:
        print(f"\n  {fname}")
        print(f"    {desc}")


if __name__ == "__main__":
    main()
