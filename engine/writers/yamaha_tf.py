"""Template-based writer for Yamaha TF Series show files (.tff).

Strategy
--------
Load an empty TF template once at module import time.
For each ``write_yamaha_tf`` call:

1. Create a fresh copy of the template's inner (decompressed) blob.
2. Locate the InputChannel data section via the same MMSXLIT heuristic the
   parser uses.
3. Overwrite parameter bytes at the TF-specific offsets (see parser
   docstring and constants below).
4. Re-compress the modified inner blob and splice it back into the outer
   MBDF container, preserving the header and any trailing data verbatim.
5. Return the reassembled bytes.

Coverage
--------
Implemented (round-trips through parse_yamaha_tf):
* channel names (Name, 64 bytes, null-padded)
* channel colors (Color, 8 bytes, null-padded string)
* HPF enable + frequency (uint32 LE ÷10 Hz)
* EQ bands 1-4 (bypass flag, freq uint32 ÷10, gain int16 ÷100, Q uint16 ÷1000)
* gate enable + threshold + attack + hold + decay (release)
* compressor enable + threshold + attack + release + ratio + makeup gain

Channels beyond N_CHANNELS (129) in the source ShowFile are silently
dropped (the TF template allocates 129 input channel record slots).
"""
from __future__ import annotations

import logging
import re
import struct
import uuid
import zlib
from pathlib import Path

from models.universal import Channel, ChannelColor, ShowFile

logger = logging.getLogger(__name__)

# Yamaha MBDF outer header carries a 16-byte session UUID at offset 0x38.
# Real TF Editor regenerates this on every save; copying the template's
# value causes "couldn't access file" rejection in Editor. See the DM7
# writer for the forensic diff that confirmed this pattern across the
# Yamaha MBDF family.
_UUID_OFFSET = 0x38
_UUID_LENGTH = 16

# ---------------------------------------------------------------------------
# MBDF container constants (shared with DM7/RIVAGE)
# ---------------------------------------------------------------------------

OUTER_MAGIC         = b"#YAMAHA "
MMSXLIT_MAGIC       = b"MMSXLIT\x00"
MMSXLIT_HEADER_SIZE = 88
SCHEMA_SIZE_OFFSET  = 80

# ---------------------------------------------------------------------------
# TF record layout constants (mirrors parsers/yamaha_tf.py)
# ---------------------------------------------------------------------------

RECORD_SIZE = 515
# Real input channel count is 40 (slots 0-39). The parser's earlier estimate
# of 129 was wrong — it came from dividing the data region size by record
# size, but channels 41+ aren't actually InputChannel records. Bytes past
# slot 40 belong to other file sections (scene data, matrices, etc.) and
# MUST NOT be overwritten, or the TF Editor rejects the file.
N_CHANNELS  = 40

NAME_OFFSET,  NAME_LEN  = 16, 64
COLOR_OFFSET, COLOR_LEN = 80,  8

HPF_ON_OFFSET   = 138
HPF_FREQ_OFFSET = 139          # uint32 LE, value × 10 = Hz

EQ_BAND_START = 144
EQ_BAND_SIZE  = 9              # bypass(1) + freq_u32(4) + gain_i16(2) + Q_u16(2)
N_EQ_BANDS    = 4

GATE_ON_OFFSET        = 224
GATE_THRESHOLD_OFFSET = 241   # int16 LE, value ÷ 100 = dBFS
GATE_ATTACK_OFFSET    = 243   # uint8, ms
GATE_HOLD_OFFSET      = 246   # uint32 LE, µs
GATE_DECAY_OFFSET     = 250   # uint32 LE, µs  → Gate.release

COMP_ON_OFFSET        = 254
COMP_THRESHOLD_OFFSET = 273   # int16 LE, value ÷ 100 = dBFS
COMP_ATTACK_OFFSET    = 275   # uint8, ms
COMP_RELEASE_OFFSET   = 276   # uint32 LE, µs
COMP_RATIO_OFFSET     = 280   # uint8, ÷ 10 = ratio (e.g. 40 → 4.0)
COMP_OUTGAIN_OFFSET   = 289   # int16 LE, ÷ 100 = dB → Compressor.makeup_gain

# ---------------------------------------------------------------------------
# Color encoding (inverse of parsers.yamaha_tf._COLOR_MAP)
# ---------------------------------------------------------------------------

_COLOR_TO_STR: dict[ChannelColor, str] = {
    ChannelColor.BLUE:   "Blue",
    ChannelColor.RED:    "Red",
    ChannelColor.GREEN:  "Green",
    ChannelColor.YELLOW: "Yellow",
    ChannelColor.PURPLE: "Purple",
    ChannelColor.CYAN:   "Cyan",
    ChannelColor.WHITE:  "White",
    ChannelColor.OFF:    "Blue",   # No OFF in TF palette; default to Blue
}

# ---------------------------------------------------------------------------
# Template loading + MBDF decompress/recompress helpers
# ---------------------------------------------------------------------------

TEMPLATE_PATH = Path(__file__).parent / "templates" / "tf_empty.tff"
_TEMPLATE_BYTES: bytes = TEMPLATE_PATH.read_bytes()


def _find_zlib_offset(data: bytes) -> int:
    """Return the byte offset of the first valid zlib-compressed MBDF block."""
    for m in re.finditer(rb"\x78[\x01\x5e\x9c\xda]", data[40:]):
        pos = m.start() + 40
        try:
            do = zlib.decompressobj()
            inner = do.decompress(data[pos:])
            if inner.startswith(OUTER_MAGIC):
                return pos
        except zlib.error:
            continue
    raise ValueError("No valid compressed MBDF block found in template")


def _decompress_inner(data: bytes, zlib_offset: int) -> tuple[bytes, bytes]:
    """Decompress the inner blob and return (inner_bytes, trailing_bytes).

    *trailing_bytes* is any data after the zlib block in *data* that must be
    preserved verbatim in the output (TF files carry additional sections
    after the main backup blob).
    """
    do = zlib.decompressobj()
    inner = do.decompress(data[zlib_offset:])
    trailing = do.unused_data
    return inner, trailing


def _find_data_start(inner: bytes) -> int:
    """Locate the start of the InputChannel binary section in the inner blob."""
    mmsxlit_pos = inner.index(MMSXLIT_MAGIC)
    schema_size = struct.unpack_from("<I", inner, mmsxlit_pos + SCHEMA_SIZE_OFFSET)[0]
    return mmsxlit_pos + MMSXLIT_HEADER_SIZE + schema_size


def _recompress(inner: bytes) -> bytes:
    # Yamaha TF Editor compresses with zlib level 1 (observed header byte
    # 0x01 after the 0x78). Re-compressing at any other level produces a
    # valid zlib blob that our own parser accepts but the real TF Editor
    # rejects — likely because an integrity field (or fixed offset layout)
    # ties to the exact compressed byte stream. Match the Editor exactly.
    return zlib.compress(inner, level=1)


# ---------------------------------------------------------------------------
# Per-field patch helpers
# ---------------------------------------------------------------------------

def _write_str_field(rec: bytearray, offset: int, max_len: int, value: str) -> None:
    """Encode *value* as UTF-8, truncate to *max_len*, null-pad to *max_len*."""
    encoded = value.encode("utf-8", errors="replace")[:max_len]
    encoded = encoded.ljust(max_len, b"\x00")
    rec[offset : offset + max_len] = encoded


def _patch_channel(rec: bytearray, channel: Channel) -> None:
    """Patch all supported fields of one TF InputChannel record."""
    # --- Name ---
    _write_str_field(rec, NAME_OFFSET, NAME_LEN, channel.name or "")

    # --- Color ---
    color_str = _COLOR_TO_STR.get(channel.color, "Blue")
    _write_str_field(rec, COLOR_OFFSET, COLOR_LEN, color_str)

    # --- HPF ---
    rec[HPF_ON_OFFSET] = 1 if channel.hpf_enabled else 0
    freq_raw = max(0, round(channel.hpf_frequency * 10))
    struct.pack_into("<I", rec, HPF_FREQ_OFFSET, freq_raw)

    # --- EQ bands ---
    for i, band in enumerate(channel.eq_bands[:N_EQ_BANDS]):
        base = EQ_BAND_START + i * EQ_BAND_SIZE
        # bypass flag (bit 0 = 1 means bypassed / disabled)
        rec[base] = 0 if band.enabled else 1
        freq_raw_eq = max(0, round(band.frequency * 10))
        struct.pack_into("<I", rec, base + 1, freq_raw_eq)
        gain_raw = max(-32768, min(32767, round(band.gain * 100)))
        struct.pack_into("<h", rec, base + 5, gain_raw)
        q_raw = max(0, min(65535, round(band.q * 1000)))
        struct.pack_into("<H", rec, base + 7, q_raw)

    # --- Gate ---
    gate = channel.gate
    if gate is not None:
        rec[GATE_ON_OFFSET] = 1 if gate.enabled else 0
        thresh_raw = max(-32768, min(32767, round(gate.threshold * 100)))
        struct.pack_into("<h", rec, GATE_THRESHOLD_OFFSET, thresh_raw)
        rec[GATE_ATTACK_OFFSET] = max(0, min(255, round(gate.attack)))
        hold_us = max(0, round(gate.hold * 1000))
        struct.pack_into("<I", rec, GATE_HOLD_OFFSET, hold_us)
        decay_us = max(0, round(gate.release * 1000))
        struct.pack_into("<I", rec, GATE_DECAY_OFFSET, decay_us)

    # --- Compressor ---
    comp = channel.compressor
    if comp is not None:
        rec[COMP_ON_OFFSET] = 1 if comp.enabled else 0
        thresh_raw = max(-32768, min(32767, round(comp.threshold * 100)))
        struct.pack_into("<h", rec, COMP_THRESHOLD_OFFSET, thresh_raw)
        rec[COMP_ATTACK_OFFSET] = max(0, min(255, round(comp.attack)))
        release_us = max(0, round(comp.release * 1000))
        struct.pack_into("<I", rec, COMP_RELEASE_OFFSET, release_us)
        ratio_raw = max(0, min(255, round(comp.ratio * 10)))
        rec[COMP_RATIO_OFFSET] = ratio_raw
        gain_raw = max(-32768, min(32767, round(comp.makeup_gain * 100)))
        struct.pack_into("<h", rec, COMP_OUTGAIN_OFFSET, gain_raw)


# ---------------------------------------------------------------------------
# Pre-compute template decomposition once at import time
# ---------------------------------------------------------------------------

_ZLIB_OFFSET  = _find_zlib_offset(_TEMPLATE_BYTES)
_INNER_BYTES, _TRAILING_BYTES = _decompress_inner(_TEMPLATE_BYTES, _ZLIB_OFFSET)
_DATA_START   = _find_data_start(_INNER_BYTES)
_OUTER_HEADER = _TEMPLATE_BYTES[:_ZLIB_OFFSET]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_yamaha_tf(show: ShowFile) -> bytes:
    """Render *show* into a Yamaha TF Series .tff binary file.

    The empty TF template is decomposed once at module import time.
    Each call gets a fresh ``bytearray`` copy of the inner blob, patches
    the channel records, re-compresses, and splices back into the outer
    MBDF container.

    Channels beyond ``N_CHANNELS`` (129) are silently dropped.

    Parameters
    ----------
    show : ShowFile
        Universal model populated by any source-format parser.

    Returns
    -------
    bytes
        Valid .tff binary, loadable by the TF parser.
    """
    # Fresh mutable copy of the decompressed inner blob.
    inner = bytearray(_INNER_BYTES)

    written = 0
    for ch_idx, channel in enumerate(show.channels):
        if ch_idx >= N_CHANNELS:
            logger.warning(
                "write_yamaha_tf: channel %d beyond limit (%d); skipping",
                ch_idx + 1, N_CHANNELS,
            )
            break

        rec_off = _DATA_START + ch_idx * RECORD_SIZE
        if rec_off + RECORD_SIZE > len(inner):
            logger.warning(
                "write_yamaha_tf: template too small for channel %d; stopping",
                ch_idx + 1,
            )
            break

        rec = bytearray(inner[rec_off : rec_off + RECORD_SIZE])
        _patch_channel(rec, channel)
        inner[rec_off : rec_off + RECORD_SIZE] = rec
        written += 1

    logger.info("write_yamaha_tf: patched %d channels", written)

    new_zlib = _recompress(bytes(inner))

    # Regenerate the per-save UUID in the outer header so Editor accepts.
    outer = bytearray(_OUTER_HEADER)
    outer[_UUID_OFFSET:_UUID_OFFSET + _UUID_LENGTH] = uuid.uuid4().bytes

    # Reassemble: outer header + new compressed block + trailing sections
    return bytes(outer) + new_zlib + _TRAILING_BYTES


__all__ = ["write_yamaha_tf"]
