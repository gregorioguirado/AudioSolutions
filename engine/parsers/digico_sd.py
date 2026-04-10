from pathlib import Path
from lxml import etree

from models.universal import (
    ShowFile, Channel, EQBand, Gate, Compressor,
    ChannelColor, EQBandType
)

DIGICO_COLOR_MAP: dict[str, ChannelColor] = {
    "1": ChannelColor.RED,
    "2": ChannelColor.GREEN,
    "3": ChannelColor.YELLOW,
    "4": ChannelColor.BLUE,
    "5": ChannelColor.PURPLE,
    "6": ChannelColor.CYAN,
    "7": ChannelColor.WHITE,
    "0": ChannelColor.OFF,
}

DIGICO_EQ_TYPE_MAP: dict[str, EQBandType] = {
    "PEQ": EQBandType.PEAK,
    "LPF": EQBandType.HIGH_CUT,
    "HPF": EQBandType.LOW_CUT,
    "LSH": EQBandType.LOW_SHELF,
    "HSH": EQBandType.HIGH_SHELF,
}


def _text(element, tag: str, default: str = "") -> str:
    node = element.find(tag)
    return node.text.strip() if node is not None and node.text else default


def _float(element, tag: str, default: float = 0.0) -> float:
    try:
        return float(_text(element, tag))
    except (ValueError, TypeError):
        return default


def _bool(element, tag: str, default: bool = False) -> bool:
    val = _text(element, tag)
    return val == "1" if val in ("0", "1") else default


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _parse_channel(ch_elem) -> Channel:
    ch_id = _safe_int(ch_elem.get("Number", "0"))
    name = _text(ch_elem, "Name")
    colour_val = _text(ch_elem, "Colour", "7")
    color = DIGICO_COLOR_MAP.get(colour_val, ChannelColor.WHITE)

    input_str = _text(ch_elem, "Input", "0")
    input_patch = _safe_int(input_str) if input_str != "0" else None

    hpf_elem = ch_elem.find("HPF")
    hpf_enabled = _bool(hpf_elem, "Enabled") if hpf_elem is not None else False
    hpf_frequency = _float(hpf_elem, "Frequency", 80.0) if hpf_elem is not None else 80.0

    eq_bands: list[EQBand] = []
    eq_elem = ch_elem.find("EQ")
    if eq_elem is not None:
        for band_elem in eq_elem.findall("Band"):
            type_str = _text(band_elem, "Type", "PEQ")
            eq_bands.append(EQBand(
                frequency=_float(band_elem, "Frequency", 1000.0),
                gain=_float(band_elem, "Gain", 0.0),
                q=_float(band_elem, "Q", 1.0),
                band_type=DIGICO_EQ_TYPE_MAP.get(type_str, EQBandType.PEAK),
                enabled=_bool(band_elem, "Enabled", True),
            ))

    gate: Gate | None = None
    gate_elem = ch_elem.find("Gate")
    if gate_elem is not None:
        gate = Gate(
            threshold=_float(gate_elem, "Threshold", -40.0),
            attack=_float(gate_elem, "Attack", 5.0),
            hold=_float(gate_elem, "Hold", 50.0),
            release=_float(gate_elem, "Release", 200.0),
            enabled=_bool(gate_elem, "Enabled", False),
        )

    compressor: Compressor | None = None
    comp_elem = ch_elem.find("Compressor")
    if comp_elem is not None:
        compressor = Compressor(
            threshold=_float(comp_elem, "Threshold", -10.0),
            ratio=_float(comp_elem, "Ratio", 1.0),
            attack=_float(comp_elem, "Attack", 5.0),
            release=_float(comp_elem, "Release", 100.0),
            makeup_gain=_float(comp_elem, "MakeUp", 0.0),
            enabled=_bool(comp_elem, "Enabled", False),
        )

    mix_buses: list[int] = []
    busses_elem = ch_elem.find("Busses")
    if busses_elem is not None:
        for bus_elem in busses_elem.findall("Bus"):
            if bus_elem.get("Enabled") == "1":
                mix_buses.append(_safe_int(bus_elem.get("Number", "0")))

    vcas: list[int] = []
    vcas_elem = ch_elem.find("VCAs")
    if vcas_elem is not None:
        for vca_elem in vcas_elem.findall("VCA"):
            if vca_elem.get("Enabled") == "1":
                vcas.append(_safe_int(vca_elem.get("Number", "0")))

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


def parse_digico_sd(filepath: Path) -> ShowFile:
    """Parse a DiGiCo SD/Quantum .show file into the universal ShowFile model."""
    show = ShowFile(source_console="digico_sd")

    with open(filepath, "rb") as f:
        root = etree.fromstring(f.read())

    channels_elem = root.find("Channels")
    if channels_elem is None:
        raise ValueError("No <Channels> element found in DiGiCo show file")

    for ch_elem in channels_elem.findall("Channel"):
        show.channels.append(_parse_channel(ch_elem))

    return show
