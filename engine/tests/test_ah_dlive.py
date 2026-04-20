"""Tests for A&H dLive parser/writer stubs.

These tests verify that the stubs are registered and raise NotImplementedError
(not ImportError or AttributeError) — so the rest of the system knows they
exist and what's blocking them.
"""
import pytest
from pathlib import Path
from parsers.ah_dlive import parse_ah_dlive
from writers.ah_dlive import write_ah_dlive
from translator import PARSERS, WRITERS, translate, UnsupportedConsolePair


def test_ah_dlive_parser_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="pending calibration"):
        parse_ah_dlive(Path("dummy.AHsession"))


def test_ah_dlive_writer_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="pending calibration"):
        write_ah_dlive(None)


def test_ah_dlive_registered_in_parsers():
    assert "ah_dlive" in PARSERS


def test_ah_dlive_registered_in_writers():
    assert "ah_dlive" in WRITERS
