from lxml import etree
from models.universal import (
    ShowFile, Channel, EQBand, Gate, Compressor,
    ChannelColor, EQBandType
)

# Universal ChannelColor → DiGiCo integer colour code
DIGICO_COLOR_MAP: dict[ChannelColor, str] = {
    ChannelColor.RED: "1",
    ChannelColor.GREEN: "2",
    ChannelColor.YELLOW: "3",
    ChannelColor.BLUE: "4",
    ChannelColor.PURPLE: "5",
    ChannelColor.CYAN: "6",
    ChannelColor.WHITE: "7",
    ChannelColor.OFF: "0",
}

DIGICO_EQ_TYPE_MAP: dict[EQBandType, str] = {
    EQBandType.PEAK: "PEQ",
    EQBandType.HIGH_CUT: "LPF",
    EQBandType.LOW_CUT: "HPF",
    EQBandType.LOW_SHELF: "LSH",
    EQBandType.HIGH_SHELF: "HSH",
}


def _sub(parent, tag: str, text: str = "") -> etree._Element:
    el = etree.SubElement(parent, tag)
    el.text = text
    return el


def _write_channel(channel: Channel) -> etree._Element:
    ch_elem = etree.Element("Channel", Number=str(channel.id))

    _sub(ch_elem, "Name", channel.name)
    _sub(ch_elem, "Colour", DIGICO_COLOR_MAP.get(channel.color, "7"))
    _sub(ch_elem, "Input", str(channel.input_patch) if channel.input_patch else "0")

    hpf = etree.SubElement(ch_elem, "HPF")
    _sub(hpf, "Enabled", "1" if channel.hpf_enabled else "0")
    _sub(hpf, "Frequency", str(channel.hpf_frequency))

    eq = etree.SubElement(ch_elem, "EQ")
    for i, band in enumerate(channel.eq_bands, start=1):
        b = etree.SubElement(eq, "Band", Number=str(i))
        _sub(b, "Type", DIGICO_EQ_TYPE_MAP.get(band.band_type, "PEQ"))
        _sub(b, "Frequency", str(band.frequency))
        _sub(b, "Gain", str(band.gain))
        _sub(b, "Q", str(band.q))
        _sub(b, "Enabled", "1" if band.enabled else "0")

    gate = etree.SubElement(ch_elem, "Gate")
    if channel.gate:
        _sub(gate, "Enabled", "1" if channel.gate.enabled else "0")
        _sub(gate, "Threshold", str(channel.gate.threshold))
        _sub(gate, "Attack", str(channel.gate.attack))
        _sub(gate, "Hold", str(channel.gate.hold))
        _sub(gate, "Release", str(channel.gate.release))
    else:
        _sub(gate, "Enabled", "0")

    comp = etree.SubElement(ch_elem, "Compressor")
    if channel.compressor:
        _sub(comp, "Enabled", "1" if channel.compressor.enabled else "0")
        _sub(comp, "Threshold", str(channel.compressor.threshold))
        _sub(comp, "Ratio", str(channel.compressor.ratio))
        _sub(comp, "Attack", str(channel.compressor.attack))
        _sub(comp, "Release", str(channel.compressor.release))
        _sub(comp, "MakeUp", str(channel.compressor.makeup_gain))
    else:
        _sub(comp, "Enabled", "0")

    busses = etree.SubElement(ch_elem, "Busses")
    for bus_id in channel.mix_bus_assignments:
        etree.SubElement(busses, "Bus", Number=str(bus_id), Enabled="1")

    vcas = etree.SubElement(ch_elem, "VCAs")
    for vca_id in channel.vca_assignments:
        etree.SubElement(vcas, "VCA", Number=str(vca_id), Enabled="1")

    return ch_elem


def write_digico_sd(show: ShowFile) -> bytes:
    """Write a universal ShowFile to DiGiCo SD/Quantum XML format."""
    root = etree.Element("Show", ConsoleType="SD12", SoftwareVersion="B179")
    channels_elem = etree.SubElement(root, "Channels")

    for channel in show.channels:
        channels_elem.append(_write_channel(channel))

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)
