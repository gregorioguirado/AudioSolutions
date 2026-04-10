#!/usr/bin/env python3
"""
Run this on a real Yamaha .cle or DiGiCo .show file to document its format.
Usage: python tools/examine_file.py path/to/file.cle
"""
import sys
import zipfile
import os


def examine_file(filepath: str) -> None:
    print(f"\n=== Examining: {filepath} ===\n")

    if not os.path.exists(filepath):
        print("ERROR: file not found")
        return

    file_size = os.path.getsize(filepath)
    print(f"File size: {file_size} bytes")

    # Check if ZIP archive
    if zipfile.is_zipfile(filepath):
        print("Format: ZIP archive")
        with zipfile.ZipFile(filepath) as zf:
            print(f"\nContents ({len(zf.namelist())} files):")
            for name in zf.namelist():
                info = zf.getinfo(name)
                print(f"  [{info.file_size:>8} bytes]  {name}")
                with zf.open(name) as f:
                    preview = f.read(400)
                    try:
                        text = preview.decode("utf-8")
                    except UnicodeDecodeError:
                        text = f"[binary: {preview[:20].hex()}...]"
                    print(f"             Preview: {text[:200].strip()}\n")
        return

    # Check if XML / text
    with open(filepath, "rb") as f:
        header = f.read(100)

    if header.lstrip().startswith(b"<?xml") or header.lstrip().startswith(b"<"):
        print("Format: XML text file")
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(2000)
        print("\nFirst 2000 chars:\n")
        print(content)
        return

    # Binary / unknown
    print("Format: Binary / unknown")
    print(f"Header hex: {header.hex()}")
    print(f"Header bytes: {header}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/examine_file.py <path/to/showfile>")
        sys.exit(1)
    examine_file(sys.argv[1])
