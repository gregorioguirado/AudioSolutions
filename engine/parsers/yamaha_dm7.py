"""Parser for Yamaha DM7 series show files (.dm7f).

File structure:
  #YAMAHA MBDFProjectFile outer container
    → ProjectInfo metadata (uncompressed)
    → zlib-compressed inner blob (#YAMAHA MBDFBackup)
         → #MMS FIELD: Mixing  (MMSXLIT schema + InputChannel binary data)
         → #MMS FIELD: Process (HeadAmp/preamp)
         → #MMS FIELD: FX, PremiumRack, Scene, Preset, ...

Offset map derived from:
  - C:/Program Files/YAMAHA/DM7/Descriptor/mms_Mixing.xml
  - Empirical calibration against dm7_empty.dm7f / dm7_named.dm7f
  - Verified against real show file "Bertoleza Sesi Campinas.dm7f"

All offsets are within a 1785-byte InputChannel record.
GainGang and DelayGang (bit type) are packed into 1 byte, making all
subsequent offsets 1 byte less than the descriptor's cumulative sum.
"""
from __future__ import annotations

import logging
import re
import struct
import zlib
from typing import Optional

from models.universal import (
    Channel, ChannelColor, Compressor, EQBand, EQBandType, Gate, ShowFile,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MBDF container constants
# ---------------------------------------------------------------------------

OUTER_MAGIC   = b"#YAMAHA "
INNER_MAGIC   = b"#YAMAHA MBDFBackup"
MMSXLIT_MAGIC = b"MMSXLIT\x00"
MIXING_FIELD  = b"#MMS FIELD\x00\x00Mixing"

# The MMSXLIT header is exactly 88 bytes long.
# schema_size is a uint32_le at MMSXLIT_pos + 80.
MMSXLIT_HEADER_SIZE  = 88
SCHEMA_SIZE_OFFSET   = 80  # relative to MMSXLIT magic

# InputChannel record layout (from mms_Mixing.xml, empirically verified)
RECORD_SIZE  = 1785
MAX_CHANNELS = 120

# --- Offsets within one 1785-byte InputChannel record ---
NAME_OFFSET      = 10    # Label.Name  — string, 64 bytes null-padded
COLOR_OFFSET     = 74    # Label.Color — string,  8 bytes null-padded
HPF_ON_OFFSET    = 134   # HPF.On        — bit (0=off, 1=on, default 0)
HPF_FREQ_OFFSET  = 135   # HPF.Frequency — uint32_t, units of 0.1 Hz (default 800 = 80 Hz)
HPF_SLOPE_OFFSET = 139   # HPF.Slope     — uint8_t, direct dB/oct (6/12/18/24, default 12)
PHASE_OFFSET     = 108   # Input.Phase   — bit (0/1)
FADER_OFFSET     = 1772  # Fader.Level   — int16_t (encoding TBD, 0 = 0dB nominal)
DCA_OFFSET       = 1767  # DCA.Assign    — 3 bytes, 24-bit mask (1 bit per DCA)
MUTE_GRP_OFFSET  = 1770  # MuteGroup.Assign — 2 bytes, 12-bit mask

NAME_LEN  = 64
COLOR_LEN = 8

# TODO: EQ band offsets need calibration files with known EQ values
# PEQ.Bank starts at ~186 within record; each bank is ~295 bytes
# TODO: Dynamics (gate/comp) offsets need further calibration

# ---------------------------------------------------------------------------
# Color mapping
# ---------------------------------------------------------------------------

_COLOR_MAP: dict[str, ChannelColor] = {
    "Blue":   ChannelColor.BLUE,
    "Red":    ChannelColor.RED,
    "Green":  ChannelColor.GREEN,
    "Yellow": ChannelColor.YELLOW,
    "Purple": ChannelColor.PURPLE,
    "Cyan":   ChannelColor.CYAN,
    "White":  ChannelColor.WHITE,
}


def _map_color(raw: str) -> ChannelColor:
    return _COLOR_MAP.get(raw, ChannelColor.BLUE)


# ---------------------------------------------------------------------------
# MBDF parsing helpers
# ---------------------------------------------------------------------------

def _decompress_inner(data: bytes) -> bytes:
    """Find and decompress the inner MBDFBackup blob.

    Searches for zlib magic bytes after the outer 40-byte header and tries
    each candidate until one decompresses to a valid MBDF blob.
    """
    for m in re.finditer(rb"\x78[\x01\x5e\x9c\xda]", data[40:]):
        pos = m.start() + 40
        try:
            inner = zlib.decompress(data[pos:])
            if inner.startswith(OUTER_MAGIC):
                return inner
        except zlib.error:
            continue
    raise ValueError("No valid compressed MBDF block found in file")


def _find_data_start(inner: bytes) -> int:
    """Return the byte offset of the first InputChannel record.

    Locates the MMSXLIT header for the Mixing section, reads the schema
    size, and steps past the schema to the binary data section.
    """
    mmsxlit_pos = inner.index(MMSXLIT_MAGIC)
    schema_size = struct.unpack_from("<I", inner, mmsxlit_pos + SCHEMA_SIZE_OFFSET)[0]
    return mmsxlit_pos + MMSXLIT_HEADER_SIZE + schema_size


def _read_str(data: bytes, offset: int, max_len: int) -> str:
    raw = data[offset : offset + max_len]
    return raw.split(b"\x00")[0].decode("utf-8", errors="replace").strip()


# ---------------------------------------------------------------------------
# Public parse entry point
# ---------------------------------------------------------------------------

def parse(data: bytes) -> ShowFile:
    """Parse a Yamaha DM7 .dm7f file and return a universal ShowFile."""
    if not data.startswith(OUTER_MAGIC):
        raise ValueError("Not a Yamaha MBDF file (missing #YAMAHA header)")

    try:
        inner = _decompress_inner(data)
    except ValueError as e:
        raise ValueError(f"Failed to decompress DM7 show data: {e}") from e

    try:
        data_start = _find_data_start(inner)
    except (ValueError, struct.error) as e:
        raise ValueError(f"Could not locate Mixing data section: {e}") from e

    channels: list[Channel] = []
    dropped: list[str] = []

    for i in range(MAX_CHANNELS):
        rec = data_start + i * RECORD_SIZE
        if rec + RECORD_SIZE > len(inner):
            break

        name  = _read_str(inner, rec + NAME_OFFSET, NAME_LEN) or f"Ch {i + 1}"
        color = _map_color(_read_str(inner, rec + COLOR_OFFSET, COLOR_LEN))

        hpf_on    = bool(inner[rec + HPF_ON_OFFSET] & 0x01)
        hpf_raw   = struct.unpack_from("<I", inner, rec + HPF_FREQ_OFFSET)[0]
        hpf_hz    = hpf_raw / 10.0

        phase_on  = bool(inner[rec + PHASE_OFFSET] & 0x01)

        dca_bytes = inner[rec + DCA_OFFSET : rec + DCA_OFFSET + 3]
        dca_mask  = int.from_bytes(dca_bytes, "little")
        dcas      = [g + 1 for g in range(24) if dca_mask & (1 << g)]

        mg_bytes  = inner[rec + MUTE_GRP_OFFSET : rec + MUTE_GRP_OFFSET + 2]
        mg_mask   = int.from_bytes(mg_bytes, "little")
        mute_grps = [g + 1 for g in range(12) if mg_mask & (1 << g)]

        ch = Channel(
            id=i + 1,
            name=name,
            color=color,
            input_patch=None,
            hpf_frequency=hpf_hz,
            hpf_enabled=hpf_on,
            eq_bands=[],        # TODO: calibrate PEQ offsets
            gate=None,          # TODO: calibrate Dynamics offsets
            compressor=None,    # TODO: calibrate Dynamics offsets
            mix_bus_assignments=[],  # TODO: ToMix offset map
            vca_assignments=dcas,
            muted=False,        # TODO: On/Off channel flag offset
        )
        channels.append(ch)

    if not channels:
        raise ValueError("No channels extracted — file may be corrupt or unsupported")

    logger.info(
        "DM7 parse complete: %d channels, first=%r",
        len(channels),
        channels[0].name if channels else "—",
    )
    return ShowFile(source_console="yamaha_dm7", channels=channels, dropped_parameters=dropped)
