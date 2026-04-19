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

InputChannel layout:
  +0    GainGang+DelayGang packed (1 byte)
  +1    Signal (9 bytes)
  +10   Label (84 bytes: Name str64 + Color str8 + Icon str12)
  +94   InPatch (9 bytes)
  +103  VirtualSC (5 bytes)
  +108  Input (3 bytes: Phase bit + Gain int16)
  +111  Insert (18 bytes)
  +129  DirectOut (5 bytes)
  +134  HPF[4] (24 bytes: 4 × On:bit + Freq:uint32 + Slope:uint8)
  +158  LPF[4] (24 bytes: same)
  +182  PEQ (294 bytes): Select + ActorSelect + 4×Bank(73 bytes each)
  +476  Proc (1 byte)
  +477  Dynamics[0] Gate/Comp1 (422 bytes): Select + ActorSelect + 4×Bank(74 bytes)
  +899  Dynamics[1] Comp2 (422 bytes): same layout
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

# PEQ layout (offsets within InputChannel record)
# Verified: dm7_empty.dm7f defaults, Bertoleza Sesi Campinas.dm7f real values
PEQ_OFFSET       = 182
PEQ_ACTOR_OFFSET = PEQ_OFFSET + 1  # uint8_t: active bank index 0-3
PEQ_BANK_0       = PEQ_OFFSET + 2  # first bank
PEQ_BANK_SIZE    = 73

# Within each PEQ bank (relative to bank start)
_PB_ON          = 0   # bit
_PB_TYPE        = 1   # string(12)
_PB_ATT         = 13  # int16_t, ÷100 → dB
_PB_BAND_FIRST  = 15  # start of 4 × Band(9 bytes)
_PB_BAND_SIZE   = 9
_PB_LOWSHELF    = 51  # bit: Band 1 is Low Shelf when set
_PB_HIGHSHELF   = 54  # bit: Band 4 is High Shelf when set
# Within each Band (relative to band start)
_BD_BYPASS      = 0   # bit
_BD_FREQ        = 1   # uint32_t, ÷10 → Hz
_BD_GAIN        = 5   # int16_t, ÷100 → dB
_BD_Q           = 7   # uint16_t, ÷1000

# Dynamics layout (offsets within InputChannel record)
# Two Dynamics units: [0] typically Gate, [1] typically Compressor
# Parameter[0] = threshold (÷100 → dB, verified from defaults and real files).
# Parameter[1..9] scaling is type-dependent and not yet calibrated.
DYN_OFFSET    = 477
DYN_SIZE      = 422
DYN_BANK_SIZE = 74
# Within each Dynamics bank (relative to bank start)
_DB_ON    = 0   # bit
_DB_TYPE  = 1   # string(16): "GATE", "Classic Comp", "PM Comp", "DE-ESSER", etc.
_DB_PARAM = 18  # 10 × int32_t; [0]=threshold ÷100 dB, rest type-dependent

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


def _parse_eq(rec: bytes) -> list[EQBand]:
    """Extract 4 PEQ bands from the active bank of a 1785-byte channel record."""
    actor = rec[PEQ_ACTOR_OFFSET]
    bank = PEQ_BANK_0 + actor * PEQ_BANK_SIZE

    low_shelf  = bool(rec[bank + _PB_LOWSHELF]  & 0x01)
    high_shelf = bool(rec[bank + _PB_HIGHSHELF] & 0x01)
    band_types = [
        EQBandType.LOW_SHELF  if low_shelf  else EQBandType.PEAK,
        EQBandType.PEAK,
        EQBandType.PEAK,
        EQBandType.HIGH_SHELF if high_shelf else EQBandType.PEAK,
    ]

    bands: list[EQBand] = []
    for i in range(4):
        bd = band_types[i]
        off = bank + _PB_BAND_FIRST + i * _PB_BAND_SIZE
        bypass  = bool(rec[off + _BD_BYPASS] & 0x01)
        freq_hz = struct.unpack_from("<I", rec, off + _BD_FREQ)[0] / 10.0
        gain_db = struct.unpack_from("<h", rec, off + _BD_GAIN)[0] / 100.0
        q       = struct.unpack_from("<H", rec, off + _BD_Q)[0]   / 1000.0
        bands.append(EQBand(
            frequency=freq_hz,
            gain=gain_db,
            q=q,
            band_type=bd,
            enabled=not bypass,
        ))
    return bands


# Dynamics types that map to Gate in the universal model
_GATE_TYPES = {"GATE", "EXP.1:2", "EXP.1:4", "DUCKER", "FREQ.DUCK"}
# Types that map to Compressor
_COMP_TYPES = {"Classic Comp", "PM Comp", "COMPANDER H", "COMPANDER S", "VCA Comp"}


def _parse_dynamics(rec: bytes, dropped: list[str], ch_name: str) -> tuple[Optional[Gate], Optional[Compressor]]:
    """Extract gate and compressor from the two Dynamics units.

    Parameter[0] ÷ 100 = threshold dB (verified against defaults and real files).
    Other parameter scaling is type-dependent and not yet calibrated — time
    constants and ratio are omitted rather than fabricated.
    """
    gate: Optional[Gate] = None
    comp: Optional[Compressor] = None

    for d in range(2):
        dyn_base = DYN_OFFSET + d * DYN_SIZE
        actor    = rec[dyn_base + 1]
        bank     = dyn_base + 2 + actor * DYN_BANK_SIZE
        on       = bool(rec[bank + _DB_ON] & 0x01)
        dyn_type = _read_str(rec, bank + _DB_TYPE, 16)
        threshold_db = struct.unpack_from("<i", rec, bank + _DB_PARAM)[0] / 100.0

        if dyn_type in _GATE_TYPES and gate is None:
            gate = Gate(
                threshold=threshold_db,
                attack=0.0,    # scaling unverified — needs calibration file
                hold=0.0,
                release=0.0,
                enabled=on,
            )
            if on:
                dropped.append(f"{ch_name}: Gate attack/hold/release not calibrated for DM7 — set to 0")
        elif dyn_type in _COMP_TYPES and comp is None:
            comp = Compressor(
                threshold=threshold_db,
                ratio=0.0,     # scaling unverified — needs calibration file
                attack=0.0,
                release=0.0,
                makeup_gain=0.0,
                enabled=on,
            )
            if on:
                dropped.append(f"{ch_name}: Comp ratio/attack/release not calibrated for DM7 — set to 0")
        elif dyn_type not in {"", "DE-ESSER"}:
            # DE-ESSER and empty type have no universal equivalent
            if on:
                dropped.append(f"{ch_name}: DM7 dynamics type '{dyn_type}' has no universal equivalent — dropped")

    return gate, comp


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

        record = inner[rec : rec + RECORD_SIZE]
        eq_bands        = _parse_eq(record)
        gate, compressor = _parse_dynamics(record, dropped, name)

        ch = Channel(
            id=i + 1,
            name=name,
            color=color,
            input_patch=None,
            hpf_frequency=hpf_hz,
            hpf_enabled=hpf_on,
            eq_bands=eq_bands,
            gate=gate,
            compressor=compressor,
            mix_bus_assignments=[],  # TODO: ToMix offset map
            vca_assignments=dcas,
            muted=False,             # TODO: On/Off channel flag offset
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
