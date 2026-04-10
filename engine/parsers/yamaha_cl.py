import zipfile
from pathlib import Path
from lxml import etree

from models.universal import (
    ShowFile, Channel, EQBand, Gate, Compressor,
    ChannelColor, EQBandType
)

# Map Yamaha color strings → universal ChannelColor
YAMAHA_COLOR_MAP: dict[str, ChannelColor] = {
    "RED": ChannelColor.RED,
    "GREEN": ChannelColor.GREEN,
    "YELLOW": ChannelColor.YELLOW,
    "BLUE": ChannelColor.BLUE,
    "PURPLE": ChannelColor.PURPLE,
    "CYAN": ChannelColor.CYAN,
    "WHITE": ChannelColor.WHITE,
    "OFF": ChannelColor.OFF,
}

YAMAHA_EQ_TYPE_MAP: dict[str, EQBandType] = {
    "PEAK": EQBandType.PEAK,
    "LPF": EQBandType.HIGH_CUT,
    "HPF": EQBandType.LOW_CUT,
    "LSH": EQBandType.LOW_SHELF,
    "HSH": EQBandType.HIGH_SHELF,
}


def _get_text(element, xpath: str, default: str = "") -> str:
    node = element.find(xpath)
    return node.text.strip() if node is not None and node.text else default


def _get_float(element, xpath: str, default: float = 0.0) -> float:
    text = _get_text(element, xpath)
    try:
        return float(text)
    except (ValueError, TypeError):
        return default


def _get_bool(element, xpath: str, default: bool = False) -> bool:
    text = _get_text(element, xpath).lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    return default


def _parse_channel(ch_elem) -> Channel:
    ch_id = int(ch_elem.get("channelNo", "0"))
    name = _get_text(ch_elem, "Name")
    color_str = _get_text(ch_elem, "Color", "WHITE").upper()
    color = YAMAHA_COLOR_MAP.get(color_str, ChannelColor.WHITE)
    input_patch_str = _get_text(ch_elem, "Patch")
    input_patch = int(input_patch_str) if input_patch_str.isdigit() else None

    hpf_elem = ch_elem.find("HPF")
    hpf_enabled = _get_bool(hpf_elem, "On") if hpf_elem is not None else False
    hpf_frequency = _get_float(hpf_elem, "Freq", 80.0) if hpf_elem is not None else 80.0

    eq_bands: list[EQBand] = []
    eq_elem = ch_elem.find("EQ")
    if eq_elem is not None:
        for band_elem in eq_elem.findall("Band"):
            type_str = _get_text(band_elem, "Type", "PEAK").upper()
            eq_bands.append(EQBand(
                frequency=_get_float(band_elem, "Freq", 1000.0),
                gain=_get_float(band_elem, "Gain", 0.0),
                q=_get_float(band_elem, "Q", 1.0),
                band_type=YAMAHA_EQ_TYPE_MAP.get(type_str, EQBandType.PEAK),
                enabled=_get_bool(band_elem, "On", True),
            ))

    gate: Gate | None = None
    dyn1 = ch_elem.find("Dynamics1")
    if dyn1 is not None:
        gate = Gate(
            threshold=_get_float(dyn1, "Threshold", -40.0),
            attack=_get_float(dyn1, "Attack", 5.0),
            hold=_get_float(dyn1, "Hold", 50.0),
            release=_get_float(dyn1, "Decay", 200.0),
            enabled=_get_bool(dyn1, "On", False),
        )

    compressor: Compressor | None = None
    dyn2 = ch_elem.find("Dynamics2")
    if dyn2 is not None:
        compressor = Compressor(
            threshold=_get_float(dyn2, "Threshold", -10.0),
            ratio=_get_float(dyn2, "Ratio", 1.0),
            attack=_get_float(dyn2, "Attack", 5.0),
            release=_get_float(dyn2, "Release", 100.0),
            makeup_gain=_get_float(dyn2, "Gain", 0.0),
            enabled=_get_bool(dyn2, "On", False),
        )

    mix_buses: list[int] = []
    sends_elem = ch_elem.find("Sends")
    if sends_elem is not None:
        for mix_elem in sends_elem.findall("Mix"):
            if _get_bool(mix_elem, "On", False):
                mix_buses.append(int(mix_elem.get("num", "0")))

    vcas: list[int] = []
    vca_elem = ch_elem.find("VCA")
    if vca_elem is not None:
        for assign_elem in vca_elem.findall("Assign"):
            if (assign_elem.text or "").strip().lower() == "true":
                vcas.append(int(assign_elem.get("num", "0")))

    return Channel(
        id=ch_id,
        name=name,
        color=color,
        input_patch=input_patch,
        hpf_frequency=hpf_frequency,
        hpf_enabled=hpf_enabled,
        eq_bands=eq_bands,
        gate=gate,
        compressor=compressor,
        mix_bus_assignments=mix_buses,
        vca_assignments=vcas,
    )


def _find_xml_entry(zf: zipfile.ZipFile) -> str:
    """Find the primary XML entry in a Yamaha .cle ZIP.

    Prefers MixParameter.xml (the canonical Yamaha show data file).
    Falls back to the first .xml entry found if MixParameter.xml is absent,
    to handle non-standard or future archive layouts.
    """
    names = zf.namelist()
    if "MixParameter.xml" in names:
        return "MixParameter.xml"
    fallback = next((n for n in names if n.endswith(".xml")), None)
    if fallback is None:
        raise ValueError("No XML file found inside the .cle archive")
    return fallback


def parse_yamaha_cl(filepath: Path) -> ShowFile:
    """Parse a Yamaha CL/QL .cle show file into the universal ShowFile model."""
    show = ShowFile(source_console="yamaha_cl")

    with zipfile.ZipFile(filepath) as zf:
        xml_filename = _find_xml_entry(zf)
        xml_bytes = zf.read(xml_filename)

    root = etree.fromstring(xml_bytes)
    channels_elem = root.find("Channels")
    if channels_elem is None:
        raise ValueError("No <Channels> element found in Yamaha show file")

    for ch_elem in channels_elem.findall("Channel"):
        show.channels.append(_parse_channel(ch_elem))

    return show
