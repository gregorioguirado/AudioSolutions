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
