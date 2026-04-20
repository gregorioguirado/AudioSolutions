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
