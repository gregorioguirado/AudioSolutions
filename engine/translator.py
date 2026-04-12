from dataclasses import dataclass, field
from pathlib import Path

from parsers.yamaha_cl import parse_yamaha_cl
from parsers.yamaha_cl_binary import parse_yamaha_cl_binary
from parsers.digico_sd import parse_digico_sd
from writers.digico_sd import write_digico_sd
from writers.yamaha_cl import write_yamaha_cl
from models.universal import ShowFile


class UnsupportedConsolePair(Exception):
    pass


@dataclass
class TranslationResult:
    output_bytes: bytes
    channel_count: int
    translated_parameters: list[str] = field(default_factory=list)
    approximated_parameters: list[str] = field(default_factory=list)
    dropped_parameters: list[str] = field(default_factory=list)


def _parse_yamaha_auto(filepath: Path) -> ShowFile:
    """Auto-detect Yamaha file format and use the right parser.

    .CLF/.CLE (binary) = real console/editor files -> binary parser
    .cle (ZIP+XML) = synthetic test fixtures -> XML parser
    """
    with open(filepath, "rb") as f:
        header = f.read(16)

    # Binary CLF: starts with 01 00 00 00
    # Binary CLE: starts with 00 00 00 03 (UTF-16-ish text header)
    # ZIP (synthetic .cle): starts with PK (50 4B)
    if header[:2] == b"PK":
        return parse_yamaha_cl(filepath)
    else:
        return parse_yamaha_cl_binary(filepath)


PARSERS = {
    "yamaha_cl": _parse_yamaha_auto,
    "digico_sd": parse_digico_sd,
}

WRITERS = {
    "digico_sd": write_digico_sd,
    "yamaha_cl": write_yamaha_cl,
}


def _collect_translated_parameters(show: ShowFile) -> list[str]:
    """Return a list of parameter types that were successfully parsed."""
    params = ["channel_names", "channel_colors", "hpf"]
    if any(ch.input_patch is not None for ch in show.channels):
        params.append("input_patch")
    if any(ch.eq_bands for ch in show.channels):
        params.append("eq_bands")
    if any(ch.gate and ch.gate.enabled for ch in show.channels):
        params.append("gate")
    if any(ch.compressor and ch.compressor.enabled for ch in show.channels):
        params.append("compressor")
    if any(ch.mix_bus_assignments for ch in show.channels):
        params.append("mix_bus_routing")
    if any(ch.vca_assignments for ch in show.channels):
        params.append("vca_assignments")
    return params


def translate(
    source_file: Path,
    source_console: str,
    target_console: str,
) -> TranslationResult:
    """
    Parse source_file from source_console format, translate to target_console format.
    Returns a TranslationResult with output bytes and translation metadata.
    """
    if source_console == target_console:
        raise UnsupportedConsolePair(
            f"Source and target console cannot be the same: {source_console}"
        )

    parser = PARSERS.get(source_console)
    writer = WRITERS.get(target_console)

    if parser is None or writer is None:
        supported = ", ".join(PARSERS.keys())
        raise UnsupportedConsolePair(
            f"Unsupported console pair: {source_console} → {target_console}. "
            f"Supported consoles: {supported}"
        )

    show = parser(source_file)
    output_bytes = writer(show)

    # DiGiCo format cannot represent channel mute state
    if target_console == "digico_sd" and any(ch.muted for ch in show.channels):
        show.dropped_parameters.append("muted_state")

    approximated = []
    if any(ch.eq_bands for ch in show.channels):
        approximated.append("eq_band_types")
    if any(ch.compressor and ch.compressor.enabled for ch in show.channels):
        approximated.append("compressor_ratio_mapping")

    return TranslationResult(
        output_bytes=output_bytes,
        channel_count=len(show.channels),
        translated_parameters=_collect_translated_parameters(show),
        approximated_parameters=approximated,
        dropped_parameters=show.dropped_parameters,
    )
