import pytest
from pathlib import Path
from lxml import etree
from parsers.yamaha_cl import parse_yamaha_cl
from writers.digico_sd import write_digico_sd
from writers.yamaha_cl import write_yamaha_cl
from models.universal import ChannelColor, EQBandType, ShowFile, Channel
from translator import translate

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

def test_muted_channel_adds_dropped_parameter(tmp_path):
    """When any channel has muted=True, translate() records 'muted_state' in dropped_parameters for digico_sd target."""
    muted_channel = Channel(
        id=1,
        name="SNARE",
        color=ChannelColor.RED,
        input_patch=1,
        hpf_frequency=80.0,
        hpf_enabled=False,
        muted=True,
    )
    show = ShowFile(source_console="Yamaha CL5", channels=[muted_channel])
    source_file = tmp_path / "muted.cle"
    source_file.write_bytes(write_yamaha_cl(show))
    result = translate(
        source_file=source_file,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    assert "muted_state" in result.dropped_parameters

def test_no_muted_channels_does_not_add_dropped_parameter(tmp_path):
    """When no channels are muted, 'muted_state' is not added to dropped_parameters."""
    unmuted_channel = Channel(
        id=1,
        name="KICK",
        color=ChannelColor.BLUE,
        input_patch=1,
        hpf_frequency=60.0,
        hpf_enabled=False,
        muted=False,
    )
    show = ShowFile(source_console="Yamaha CL5", channels=[unmuted_channel])
    source_file = tmp_path / "unmuted.cle"
    source_file.write_bytes(write_yamaha_cl(show))
    result = translate(
        source_file=source_file,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    assert "muted_state" not in result.dropped_parameters
