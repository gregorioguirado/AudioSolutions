import pytest
from lxml import etree
from parsers.yamaha_cl import parse_yamaha_cl
from writers.digico_sd import write_digico_sd
from models.universal import ChannelColor, EQBandType

def test_write_returns_bytes(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    assert isinstance(result, bytes)

def test_write_produces_valid_xml(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    assert root.tag == "Show"

def test_write_channel_count(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    channels = root.findall(".//Channel")
    assert len(channels) == 2

def test_write_channel_name(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    assert first_channel.findtext("Name") == "KICK"

def test_write_channel_color(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    colour_val = first_channel.findtext("Colour")
    assert colour_val == "1"  # DiGiCo uses integers for colors; 1 = red

def test_write_hpf(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    hpf = first_channel.find("HPF")
    assert hpf.findtext("Enabled") == "1"
    assert float(hpf.findtext("Frequency")) == 80.0

def test_write_eq_bands(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    bands = first_channel.findall(".//Band")
    assert len(bands) == 2
    assert float(bands[0].findtext("Frequency")) == 100.0
    assert float(bands[0].findtext("Gain")) == 3.0

def test_write_gate(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    gate = first_channel.find("Gate")
    assert gate.findtext("Enabled") == "1"
    assert float(gate.findtext("Threshold")) == -40.0

def test_write_compressor(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    comp = first_channel.find("Compressor")
    assert comp.findtext("Enabled") == "1"
    assert float(comp.findtext("Threshold")) == -15.0
    assert float(comp.findtext("MakeUp")) == 3.0
