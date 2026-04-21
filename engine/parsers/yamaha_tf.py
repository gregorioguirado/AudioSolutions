"""Parser for Yamaha TF Series show files (.tff).

File structure:
  #YAMAHA MBDFProjectFile outer container  (identical to DM7/RIVAGE)
    → zlib-compressed inner blob (#YAMAHA MBDFBackup)
         → #MMS FIELD: Mixing  (MMSXLIT schema + InputChannel binary data)

InputChannel record layout (515 bytes) — empirically calibrated from
samples/tf_hpf_eq_calibration.tff and samples/tf_dynamics_calibration.tff:

  +0    Category   string 16   ignored
  +16   Name       string 64   PRIMARY channel name
  +80   Color      string 8    "Blue", "Red", etc.
  +88   Icon       string 12   ignored
  +138  HPF_ON     uint8       1=ON
  +139  HPF_FREQ   uint32 LE   ÷10 = Hz
  +144  EQ Band 1  9 bytes     bypass(1)+freq_u32(÷10Hz)+gain_i16(÷100dB)+Q_u16(÷1000)
  +153  EQ Band 2  9 bytes     same layout
  +162  EQ Band 3  9 bytes     same layout
  +171  EQ Band 4  9 bytes     same layout
  +224  GATE_ON    uint8
  +241  GATE_THRESH int16 LE   ÷100 = dBFS
  +243  GATE_ATK   uint8       ms
  +246  GATE_HOLD  uint32 LE   µs (÷1000 = ms)
  +250  GATE_DECAY uint32 LE   µs (÷1000 = ms)  → mapped to Gate.release
  +254  COMP_ON    uint8
  +273  COMP_THRESH int16 LE   ÷100 = dBFS
  +275  COMP_ATK   uint8       ms
  +276  COMP_REL   uint32 LE   µs (÷1000 = ms)
  +280  COMP_RATIO uint8       ÷10 = ratio (e.g. 40 → 4.0)
  +289  COMP_GAIN  int16 LE    ÷100 = dB  → Compressor.makeup_gain
"""
from __future__ import annotations

import logging
import re
import struct
import zlib

from models.universal import (
    Channel, ChannelColor, Compressor, EQBand, EQBandType, Gate, ShowFile,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MBDF container constants (shared with DM7/RIVAGE)
# ---------------------------------------------------------------------------

OUTER_MAGIC     = b"#YAMAHA "
MMSXLIT_MAGIC   = b"MMSXLIT\x00"
MMSXLIT_HEADER_SIZE = 88
SCHEMA_SIZE_OFFSET  = 80

# ---------------------------------------------------------------------------
# TF-series record layout constants
# ---------------------------------------------------------------------------

RECORD_SIZE  = 515
# Only the first 40 slots are real InputChannel records. Slots 41+ land in
# unrelated file sections (scene data, matrices, etc.) and parse as garbage
# (e.g. HPF frequencies of 100 MHz, EQ gains of -174 dB). Empirically confirmed
# from tf_empty.tff, DOM CASMURRO 2.tff, and the writer's byte-identity
# round-trip test. The prior 74 came from a naive divide-by-RECORD_SIZE.
MAX_CHANNELS = 40

NAME_OFFSET, NAME_LEN   = 16, 64
COLOR_OFFSET, COLOR_LEN = 80, 8

HPF_ON_OFFSET   = 138
HPF_FREQ_OFFSET = 139

EQ_BAND_START = 144
EQ_BAND_SIZE  = 9
N_EQ_BANDS    = 4

GATE_ON_OFFSET        = 224
GATE_THRESHOLD_OFFSET = 241
GATE_ATTACK_OFFSET    = 243
GATE_HOLD_OFFSET      = 246
GATE_DECAY_OFFSET     = 250

COMP_ON_OFFSET        = 254
COMP_THRESHOLD_OFFSET = 273
COMP_ATTACK_OFFSET    = 275
COMP_RELEASE_OFFSET   = 276
COMP_RATIO_OFFSET     = 280
COMP_OUTGAIN_OFFSET   = 289

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
        release=decay_us / 1000.0,  # TF calls this "Decay"; model field is "release"
        enabled=enabled,
    )


def _parse_compressor(rec: bytes) -> Compressor:
    enabled   = bool(rec[COMP_ON_OFFSET])
    threshold = struct.unpack_from("<h", rec, COMP_THRESHOLD_OFFSET)[0] / 100.0
    attack    = float(rec[COMP_ATTACK_OFFSET])
    release_us = struct.unpack_from("<I", rec, COMP_RELEASE_OFFSET)[0]
    ratio      = rec[COMP_RATIO_OFFSET] / 10.0
    makeup     = struct.unpack_from("<h", rec, COMP_OUTGAIN_OFFSET)[0] / 100.0
    return Compressor(
        threshold=threshold,
        ratio=max(ratio, 1.0),
        attack=attack,
        release=release_us / 1000.0,
        makeup_gain=makeup,
        enabled=enabled,
    )


# ---------------------------------------------------------------------------
# Public parse entry point
# ---------------------------------------------------------------------------

def parse(path: str) -> ShowFile:
    """Parse a Yamaha TF Series .tff file and return a universal ShowFile."""
    with open(path, "rb") as fh:
        data = fh.read()

    if not data.startswith(OUTER_MAGIC):
        raise ValueError("Not a Yamaha MBDF file (missing #YAMAHA header)")

    try:
        inner = _decompress_inner(data)
    except ValueError as e:
        raise ValueError(f"Failed to decompress TF show data: {e}") from e

    try:
        data_start = _find_data_start(inner)
    except (ValueError, struct.error) as e:
        raise ValueError(f"Could not locate Mixing data section: {e}") from e

    channels: list[Channel] = []

    for i in range(MAX_CHANNELS):
        rec_off = data_start + i * RECORD_SIZE
        if rec_off + RECORD_SIZE > len(inner):
            logger.warning("TF: ran out of data at channel %d — file may be truncated", i + 1)
            break

        rec = inner[rec_off : rec_off + RECORD_SIZE]

        name  = _read_str(rec, NAME_OFFSET, NAME_LEN)
        color = _map_color(_read_str(rec, COLOR_OFFSET, COLOR_LEN))

        if not name:
            logger.warning("TF: channel %d has an empty name", i + 1)
            name = f"Ch {i + 1}"

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

    logger.info("TF parse complete: %d channels, first=%r", len(channels), channels[0].name)
    return ShowFile(
        source_console="yamaha_tf",
        channels=channels,
        dropped_parameters=[],
    )
