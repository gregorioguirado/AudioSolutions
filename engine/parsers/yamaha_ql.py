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
