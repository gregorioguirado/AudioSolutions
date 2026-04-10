from models.universal import (
    ShowFile, Channel, EQBand, Gate, Compressor, ChannelColor, EQBandType
)

def test_channel_defaults():
    ch = Channel(id=1, name="KICK", color=ChannelColor.RED, input_patch=1,
                 hpf_frequency=80.0, hpf_enabled=True)
    assert ch.eq_bands == []
    assert ch.gate is None
    assert ch.compressor is None
    assert ch.mix_bus_assignments == []
    assert ch.vca_assignments == []
    assert ch.muted is False

def test_showfile_tracks_dropped_parameters():
    sf = ShowFile(source_console="yamaha_cl5")
    sf.dropped_parameters.append("yamaha_premium_rack")
    assert "yamaha_premium_rack" in sf.dropped_parameters

def test_eq_band_types():
    band = EQBand(frequency=1000.0, gain=3.0, q=1.4,
                  band_type=EQBandType.PEAK, enabled=True)
    assert band.frequency == 1000.0
    assert band.band_type == EQBandType.PEAK

def test_compressor_fields():
    comp = Compressor(threshold=-10.0, ratio=4.0, attack=5.0,
                      release=100.0, makeup_gain=2.0, enabled=True)
    assert comp.ratio == 4.0
    assert comp.enabled is True
