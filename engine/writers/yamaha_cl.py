import io
import zipfile
from lxml import etree
from models.universal import (
    ShowFile, Channel, ChannelColor, EQBandType
)

YAMAHA_COLOR_MAP: dict[ChannelColor, str] = {
    ChannelColor.RED: "RED",
    ChannelColor.GREEN: "GREEN",
    ChannelColor.YELLOW: "YELLOW",
    ChannelColor.BLUE: "BLUE",
    ChannelColor.PURPLE: "PURPLE",
    ChannelColor.CYAN: "CYAN",
    ChannelColor.WHITE: "WHITE",
    ChannelColor.OFF: "OFF",
}

YAMAHA_EQ_TYPE_MAP: dict[EQBandType, str] = {
    EQBandType.PEAK: "PEAK",
    EQBandType.HIGH_CUT: "LPF",
    EQBandType.LOW_CUT: "HPF",
    EQBandType.LOW_SHELF: "LSH",
    EQBandType.HIGH_SHELF: "HSH",
}


def _sanitize_xml_text(text: str) -> str:
    """Strip C0 control characters that lxml rejects (nulls etc.) while keeping
    printable characters and the three whitespace control chars valid in XML."""
    if not text:
        return text
    return "".join(c for c in text if ord(c) >= 32 or c in "\t\n\r")


def _sub(parent, tag: str, text: str = "") -> etree._Element:
    el = etree.SubElement(parent, tag)
    el.text = _sanitize_xml_text(text)
    return el


def _write_channel(channel: Channel) -> etree._Element:
    ch_elem = etree.Element("Channel",
                            channelNo=str(channel.id),
                            channelType="MONO")

    _sub(ch_elem, "Name", channel.name)
    _sub(ch_elem, "Color", YAMAHA_COLOR_MAP.get(channel.color, "WHITE"))
    _sub(ch_elem, "Patch", str(channel.input_patch) if channel.input_patch else "0")
    _sub(ch_elem, "On", "false" if channel.muted else "true")

    hpf = etree.SubElement(ch_elem, "HPF")
    _sub(hpf, "On", "true" if channel.hpf_enabled else "false")
    _sub(hpf, "Freq", str(int(channel.hpf_frequency)))

    eq = etree.SubElement(ch_elem, "EQ")
    for i, band in enumerate(channel.eq_bands, start=1):
        b = etree.SubElement(eq, "Band", num=str(i))
        _sub(b, "On", "true" if band.enabled else "false")
        _sub(b, "Type", YAMAHA_EQ_TYPE_MAP.get(band.band_type, "PEAK"))
        _sub(b, "Freq", str(int(band.frequency)))
        _sub(b, "Gain", str(band.gain))
        _sub(b, "Q", str(band.q))

    dyn1 = etree.SubElement(ch_elem, "Dynamics1")
    if channel.gate:
        _sub(dyn1, "On", "true" if channel.gate.enabled else "false")
        _sub(dyn1, "Threshold", str(channel.gate.threshold))
        _sub(dyn1, "Attack", str(channel.gate.attack))
        _sub(dyn1, "Hold", str(channel.gate.hold))
        _sub(dyn1, "Decay", str(channel.gate.release))
    else:
        _sub(dyn1, "On", "false")

    dyn2 = etree.SubElement(ch_elem, "Dynamics2")
    if channel.compressor:
        _sub(dyn2, "On", "true" if channel.compressor.enabled else "false")
        _sub(dyn2, "Threshold", str(channel.compressor.threshold))
        _sub(dyn2, "Ratio", str(channel.compressor.ratio))
        _sub(dyn2, "Attack", str(channel.compressor.attack))
        _sub(dyn2, "Release", str(channel.compressor.release))
        _sub(dyn2, "Gain", str(channel.compressor.makeup_gain))
    else:
        _sub(dyn2, "On", "false")

    sends = etree.SubElement(ch_elem, "Sends")
    for bus_id in channel.mix_bus_assignments:
        mix = etree.SubElement(sends, "Mix", num=str(bus_id))
        _sub(mix, "On", "true")

    vca_elem = etree.SubElement(ch_elem, "VCA")
    for vca_id in channel.vca_assignments:
        assign = etree.SubElement(vca_elem, "Assign", num=str(vca_id))
        assign.text = "true"

    return ch_elem


def write_yamaha_cl(show: ShowFile) -> bytes:
    """Write a universal ShowFile to Yamaha CL/QL .cle format (ZIP containing XML)."""
    root = etree.Element("MixConsole", version="1.0", consoleType="CL5")
    channels_elem = etree.SubElement(root, "Channels")

    for channel in show.channels:
        channels_elem.append(_write_channel(channel))

    xml_bytes = etree.tostring(root, xml_declaration=True,
                               encoding="UTF-8", pretty_print=True)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("MixParameter.xml", xml_bytes)

    return buf.getvalue()
