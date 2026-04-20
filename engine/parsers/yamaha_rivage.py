"""Parser for Yamaha RIVAGE PM series show files (.RIVAGEPM).

File structure:
  #YAMAHA MBDFProjectFile outer container  (same MBDF container as DM7/TF)
    → zlib-compressed inner blob (#YAMAHA MBDFBackup)
         → MMSXLIT schema section
         → InputChannel binary data  (144 channels × 1890 bytes = 272 160 bytes)
         → remaining sections (buses, FX, matrices) — not parsed

InputChannel record layout (1890 bytes) — empirically calibrated from
rivage_hpf_calib.RIVAGEPM and rivage_dyn_calib.RIVAGEPM (both DSP-R10 sessions):

  +0    GainGang+DelayGang   1 byte   ignored
  +1    Signal.Relation      1 byte   ignored
  +2    Signal.StereoInputType  8 bytes  "STEREO" for all input channels
  +10   Label.Name           64 bytes  PRIMARY channel name
  +74   Label.Color           8 bytes  "Blue", "Red", etc.
  +82   Label.Icon           12 bytes  ignored

  +152  HPF_ON    uint8               1=ON
  +153  HPF_FREQ  uint32 LE           ÷10 = Hz

  +193  EQ Band 1  9 bytes  bypass(1)+freq_u32(÷10Hz)+gain_i16(÷100dB)+Q_u16(÷1000)
  +202  EQ Band 2  9 bytes  same layout
  +211  EQ Band 3  9 bytes  same layout
  +220  EQ Band 4  9 bytes  same layout

  +294  GATE_ON    uint8
  +409  GATE_THRESH  int16 LE    ÷100 = dBFS
  +411  GATE_ATK     uint8       ms
  +414  GATE_HOLD    uint32 LE   µs (÷1000 = ms)
  +418  GATE_DECAY   uint32 LE   µs (÷1000 = ms)  → mapped to Gate.release

  +690  COMP_ON    uint8
  +767  COMP_THRESH  int16 LE    ÷100 = dBFS
  +769  COMP_ATK     uint16 LE   µs (÷1000 = ms)
  +773  COMP_REL     uint16 LE   ÷10 = ms
  +775  COMP_RATIO   uint16 LE   ÷100 = ratio

Dropped: compressor knee type, compressor makeup gain (not calibrated).
"""
from __future__ import annotations

import logging
import re
import struct
import zlib
from pathlib import Path

from models.universal import (
    Channel, ChannelColor, Compressor, EQBand, EQBandType, Gate, ShowFile,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MBDF container constants
# ---------------------------------------------------------------------------

OUTER_MAGIC     = b"#YAMAHA "
MMSXLIT_MAGIC   = b"MMSXLIT\x00"
MMSXLIT_HEADER_SIZE = 88
SCHEMA_SIZE_OFFSET  = 80

# ---------------------------------------------------------------------------
# RIVAGE record layout constants
# ---------------------------------------------------------------------------

RECORD_SIZE = 1890
N_CHANNELS  = 144

NAME_OFFSET,  NAME_LEN  = 10, 64
COLOR_OFFSET, COLOR_LEN = 74,  8

HPF_ON_OFFSET   = 152
HPF_FREQ_OFFSET = 153

EQ_BAND_START = 193
EQ_BAND_SIZE  = 9
N_EQ_BANDS    = 4

GATE_ON_OFFSET        = 294
GATE_THRESHOLD_OFFSET = 409
GATE_ATTACK_OFFSET    = 411
GATE_HOLD_OFFSET      = 414
GATE_DECAY_OFFSET     = 418

COMP_ON_OFFSET        = 690
COMP_THRESHOLD_OFFSET = 767
COMP_ATTACK_OFFSET    = 769
COMP_RELEASE_OFFSET   = 773
COMP_RATIO_OFFSET     = 775

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
# MBDF helpers
# ---------------------------------------------------------------------------

def _decompress_inner(data: bytes) -> bytes:
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
    mmsxlit_pos = inner.index(MMSXLIT_MAGIC)
    schema_size = struct.unpack_from("<I", inner, mmsxlit_pos + SCHEMA_SIZE_OFFSET)[0]
    return mmsxlit_pos + MMSXLIT_HEADER_SIZE + schema_size


def _read_str(data: bytes, offset: int, max_len: int) -> str:
    return data[offset : offset + max_len].split(b"\x00")[0].decode("utf-8", errors="replace").strip()


# ---------------------------------------------------------------------------
# Per-channel field extractors
# ---------------------------------------------------------------------------

def _parse_eq(rec: bytes) -> list[EQBand]:
    bands = []
    for i in range(N_EQ_BANDS):
        base = EQ_BAND_START + i * EQ_BAND_SIZE
        bypass = bool(rec[base] & 0x01)
        freq   = struct.unpack_from("<I", rec, base + 1)[0] / 10.0
        gain   = struct.unpack_from("<h", rec, base + 5)[0] / 100.0
        q      = struct.unpack_from("<H", rec, base + 7)[0] / 1000.0
        bands.append(EQBand(
            frequency=freq,
            gain=gain,
            q=max(q, 0.1),
            band_type=EQBandType.PEAK,
            enabled=not bypass,
        ))
    return bands


def _parse_gate(rec: bytes) -> Gate:
    enabled   = bool(rec[GATE_ON_OFFSET])
    threshold = struct.unpack_from("<h", rec, GATE_THRESHOLD_OFFSET)[0] / 100.0
    attack    = float(rec[GATE_ATTACK_OFFSET])
    hold_us   = struct.unpack_from("<I", rec, GATE_HOLD_OFFSET)[0]
    decay_us  = struct.unpack_from("<I", rec, GATE_DECAY_OFFSET)[0]
    return Gate(
        threshold=threshold,
        attack=attack,
        hold=hold_us / 1000.0,
        release=decay_us / 1000.0,  # RIVAGE calls this "Decay"
        enabled=enabled,
    )


def _parse_compressor(rec: bytes) -> Compressor:
    enabled   = bool(rec[COMP_ON_OFFSET])
    threshold = struct.unpack_from("<h", rec, COMP_THRESHOLD_OFFSET)[0] / 100.0
    attack_us = struct.unpack_from("<H", rec, COMP_ATTACK_OFFSET)[0]
    release   = struct.unpack_from("<H", rec, COMP_RELEASE_OFFSET)[0] / 10.0
    ratio     = struct.unpack_from("<H", rec, COMP_RATIO_OFFSET)[0] / 100.0
    return Compressor(
        threshold=threshold,
        ratio=max(ratio, 1.0),
        attack=attack_us / 1000.0,
        release=release,
        makeup_gain=0.0,  # TODO: offset not calibrated
        enabled=enabled,
    )


# ---------------------------------------------------------------------------
# Public parse entry point
# ---------------------------------------------------------------------------

def parse(path: str) -> ShowFile:
    """Parse a Yamaha RIVAGE PM .RIVAGEPM file and return a universal ShowFile."""
    data = Path(path).read_bytes()

    if not data.startswith(OUTER_MAGIC):
        raise ValueError("Not a Yamaha MBDF file (missing #YAMAHA header)")

    try:
        inner = _decompress_inner(data)
    except ValueError as e:
        raise ValueError(f"Failed to decompress RIVAGE show data: {e}") from e

    try:
        data_start = _find_data_start(inner)
    except (ValueError, struct.error) as e:
        raise ValueError(f"Could not locate Mixing data section: {e}") from e

    channels: list[Channel] = []
    dropped: list[str] = ["compressor.knee_type", "compressor.makeup_gain"]

    for i in range(N_CHANNELS):
        rec_off = data_start + i * RECORD_SIZE
        if rec_off + RECORD_SIZE > len(inner):
            logger.warning("RIVAGE: truncated — only %d channels parsed", i)
            break

        rec = inner[rec_off : rec_off + RECORD_SIZE]

        name = _read_str(rec, NAME_OFFSET, NAME_LEN)
        if not name:
            logger.warning("RIVAGE: ch%d has empty name", i + 1)
            name = f"Ch {i + 1}"

        color    = _map_color(_read_str(rec, COLOR_OFFSET, COLOR_LEN))
        hpf_on   = bool(rec[HPF_ON_OFFSET])
        hpf_freq = struct.unpack_from("<I", rec, HPF_FREQ_OFFSET)[0] / 10.0

        channels.append(Channel(
            id=i + 1,
            name=name,
            color=color,
            input_patch=None,
            hpf_frequency=hpf_freq,
            hpf_enabled=hpf_on,
            eq_bands=_parse_eq(rec),
            gate=_parse_gate(rec),
            compressor=_parse_compressor(rec),
            mix_bus_assignments=[],
            vca_assignments=[],
            muted=False,
        ))

    if not channels:
        raise ValueError("No channels extracted — file may be corrupt or unsupported")

    logger.info("RIVAGE parse complete: %d channels, first=%r", len(channels), channels[0].name)
    return ShowFile(
        source_console="yamaha_rivage_pm",
        channels=channels,
        dropped_parameters=dropped,
    )
