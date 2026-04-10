import pytest
from parsers.yamaha_cl import parse_yamaha_cl
from models.universal import ShowFile, ChannelColor, EQBandType

def test_parse_returns_showfile(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    assert isinstance(result, ShowFile)
    assert result.source_console == "yamaha_cl"

def test_parse_channel_count(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    assert len(result.channels) == 2

def test_parse_channel_name(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    assert result.channels[0].name == "KICK"
    assert result.channels[1].name == "SNARE"

def test_parse_channel_color(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    assert result.channels[0].color == ChannelColor.RED
    assert result.channels[1].color == ChannelColor.GREEN

def test_parse_input_patch(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    assert result.channels[0].input_patch == 1
    assert result.channels[1].input_patch == 2

def test_parse_hpf(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert kick.hpf_enabled is True
    assert kick.hpf_frequency == 80.0

def test_parse_eq_bands(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert len(kick.eq_bands) == 2
    assert kick.eq_bands[0].frequency == 100.0
    assert kick.eq_bands[0].gain == 3.0
    assert kick.eq_bands[0].q == 1.4
    assert kick.eq_bands[0].band_type == EQBandType.PEAK
    assert kick.eq_bands[0].enabled is True

def test_parse_gate(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert kick.gate is not None
    assert kick.gate.enabled is True
    assert kick.gate.threshold == -40.0
    assert kick.gate.attack == 5.0
    assert kick.gate.hold == 50.0
    assert kick.gate.release == 200.0

def test_parse_compressor(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert kick.compressor is not None
    assert kick.compressor.enabled is True
    assert kick.compressor.threshold == -15.0
    assert kick.compressor.ratio == 4.0
    assert kick.compressor.makeup_gain == 3.0

def test_parse_mix_bus_assignments(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert 1 in kick.mix_bus_assignments
    assert 2 not in kick.mix_bus_assignments

def test_parse_vca_assignments(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert 1 in kick.vca_assignments

def test_parse_muted(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    # Both channels have <On>true</On>, meaning active (not muted)
    assert result.channels[0].muted is False
    assert result.channels[1].muted is False
