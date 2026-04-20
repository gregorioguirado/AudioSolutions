"""Forensic tool — binary-diff two editor-produced save files to find
volatile metadata (UUIDs, timestamps, counters) that the real editor
regenerates on every save.

Usage:
    python tools/editor_save_diff.py <file_a> <file_b>

Output:
  - Total file sizes and byte delta
  - Per-blob manifest (offset, compressed size, decompressed size)
  - All differing byte regions, labelled with in-blob vs outer-metadata
  - Heuristic classification of each outer-metadata region:
      UUID (16 bytes, high entropy, fully differ)
      COUNTER/TIMESTAMP (4 bytes, similar magnitude)
      SHIFT (large-identical-content shifted by an earlier blob size change)
      UNKNOWN (anything else)

Plugs into Track A of docs/handover/editor-accept sprint.
"""
from __future__ import annotations

import math
import sys
import zlib
from pathlib import Path


def all_blobs(data: bytes) -> list[tuple[int, int, int]]:
    """Return a list of (offset, compressed_size, decompressed_size) for
    every substantial zlib blob in *data*. Scans for the zlib magic byte
    pair 0x78 [0x01|0x5E|0x9C|0xDA] and attempts decompression."""
    out: list[tuple[int, int, int]] = []
    i = 0
    while i < len(data) - 1:
        if data[i] == 0x78 and data[i + 1] in (0x01, 0x5E, 0x9C, 0xDA):
            try:
                d = zlib.decompressobj()
                dec = d.decompress(data[i:])
                if len(dec) > 100:
                    compr_size = len(data) - i - len(d.unused_data)
                    out.append((i, compr_size, len(dec)))
                    i += compr_size
                    continue
            except zlib.error:
                pass
        i += 1
    return out


def diff_regions(a: bytes, b: bytes) -> list[tuple[int, int]]:
    """Return (start, end_exclusive) ranges where a[i] != b[i] for the
    common prefix length of the two buffers."""
    n = min(len(a), len(b))
    regs: list[tuple[int, int]] = []
    i = 0
    while i < n:
        if a[i] != b[i]:
            s = i
            while i < n and a[i] != b[i]:
                i += 1
            regs.append((s, i))
        else:
            i += 1
    return regs


def _entropy(buf: bytes) -> float:
    """Shannon entropy in bits-per-byte. 8.0 = fully random; 0 = constant."""
    if not buf:
        return 0.0
    counts = [0] * 256
    for byte in buf:
        counts[byte] += 1
    total = len(buf)
    ent = 0.0
    for c in counts:
        if c == 0:
            continue
        p = c / total
        ent -= p * math.log2(p)
    return ent


def classify_region(length: int, a_bytes: bytes, b_bytes: bytes) -> str:
    """Heuristic: is this likely a UUID, a counter/timestamp, or unknown?"""
    if length == 16:
        ea, eb = _entropy(a_bytes), _entropy(b_bytes)
        if ea > 3.0 and eb > 3.0:
            return "UUID (16B, high entropy)"
    if length in (4, 8):
        va = int.from_bytes(a_bytes, "little")
        vb = int.from_bytes(b_bytes, "little")
        if va > 0 and vb > 0:
            ratio = min(va, vb) / max(va, vb)
            if ratio > 0.5:
                return f"COUNTER/TIMESTAMP ({length}B, LE: {va} vs {vb})"
    if length == 1:
        return f"SINGLE BYTE ({a_bytes.hex()} -> {b_bytes.hex()})"
    return "UNKNOWN"


def in_blob(region_start: int, blobs: list[tuple[int, int, int]]) -> int | None:
    for idx, (off, csize, _) in enumerate(blobs):
        if off <= region_start < off + csize:
            return idx
    return None


def merge_adjacent_regions(regions: list[tuple[int, int]], max_gap: int = 1) -> list[tuple[int, int]]:
    """Merge regions separated by <= max_gap bytes. Many apparent "two
    differing regions 1 byte apart" are really one logical field split
    because a single matching byte happens to fall in the middle."""
    if not regions:
        return []
    merged = [regions[0]]
    for s, e in regions[1:]:
        last_s, last_e = merged[-1]
        if s - last_e <= max_gap:
            merged[-1] = (last_s, e)
        else:
            merged.append((s, e))
    return merged


def main():
    if len(sys.argv) != 3:
        print("Usage: python editor_save_diff.py <file_a> <file_b>")
        sys.exit(2)
    pa, pb = Path(sys.argv[1]), Path(sys.argv[2])
    a = pa.read_bytes()
    b = pb.read_bytes()

    print(f"A: {pa.name}  size={len(a)}")
    print(f"B: {pb.name}  size={len(b)}")
    print(f"Delta: {len(b) - len(a):+d} bytes")
    print()

    blobs_a = all_blobs(a)
    blobs_b = all_blobs(b)
    print(f"Blobs in A: {len(blobs_a)}")
    for i, (off, cs, ds) in enumerate(blobs_a):
        print(f"  [{i}] at {off:>6}  compressed={cs:>6}  decompressed={ds:>7}")
    print(f"Blobs in B: {len(blobs_b)}")
    for i, (off, cs, ds) in enumerate(blobs_b):
        print(f"  [{i}] at {off:>6}  compressed={cs:>6}  decompressed={ds:>7}")

    raw_regions = diff_regions(a, b)
    regions = merge_adjacent_regions(raw_regions, max_gap=1)
    print(f"\nDiff regions (common prefix, adjacent-merged): {len(regions)}")

    outer = []
    in_blob_count = 0
    for s, e in regions:
        blob_idx = in_blob(s, blobs_a)
        if blob_idx is not None:
            in_blob_count += 1
        else:
            outer.append((s, e))

    print(f"  {in_blob_count} inside zlib blobs (recompression noise, ignorable)")
    print(f"  {len(outer)} in OUTER metadata (candidate volatile fields)")

    print("\n=== Outer-metadata differences (this is where editor validates) ===")
    for s, e in outer:
        length = e - s
        ab = a[s:e]
        bb = b[s:e]
        cls = classify_region(length, ab, bb)
        print(f"  offset 0x{s:<5x} ({s:>5})  len {length:>3}  {cls}")
        print(f"    A: {ab.hex()}")
        print(f"    B: {bb.hex()}")


if __name__ == "__main__":
    main()
