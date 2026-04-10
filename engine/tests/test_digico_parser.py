import pytest
from parsers.digico_sd import parse_digico_sd
from models.universal import ShowFile, ChannelColor, EQBandType

def test_parse_returns_showfile(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    assert isinstance(result, ShowFile)
    assert result.source_console == "digico_sd"

def test_parse_channel_count(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    assert len(result.channels) == 2

def test_parse_channel_name(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    assert result.channels[0].name == "KICK"
    assert result.channels[1].name == "SNARE"

def test_parse_channel_color(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    assert result.channels[0].color == ChannelColor.RED
    assert result.channels[1].color == ChannelColor.GREEN

def test_parse_input_patch(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    assert result.channels[0].input_patch == 1

def test_parse_hpf(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert kick.hpf_enabled is True
    assert kick.hpf_frequency == 80.0

def test_parse_eq_bands(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert len(kick.eq_bands) == 2
    assert kick.eq_bands[0].frequency == 100.0
    assert kick.eq_bands[0].gain == 3.0
    assert kick.eq_bands[0].band_type == EQBandType.PEAK

def test_parse_gate(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert kick.gate is not None
    assert kick.gate.enabled is True
    assert kick.gate.threshold == -40.0

def test_parse_compressor(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert kick.compressor is not None
    assert kick.compressor.enabled is True
    assert kick.compressor.threshold == -15.0
    assert kick.compressor.makeup_gain == 3.0

def test_parse_mix_bus_assignments(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert 1 in kick.mix_bus_assignments
    assert 2 not in kick.mix_bus_assignments

def test_parse_vca_assignments(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert 1 in kick.vca_assignments
