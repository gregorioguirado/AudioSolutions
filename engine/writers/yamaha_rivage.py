"""Template-based writer for Yamaha RIVAGE PM series show files (.RIVAGEPM).

Strategy
--------
Load an empty RIVAGE template once at module import time.
For each ``write_yamaha_rivage`` call:

1. Create a fresh copy of the template's inner (decompressed) blob.
2. Locate the InputChannel data section via the same MMSXLIT heuristic the
   parser uses.
3. Overwrite parameter bytes at the RIVAGE-specific offsets (see parser
   docstring and constants below).
4. Re-compress the modified inner blob and splice it back into the outer
   MBDF container, preserving the header and any trailing data verbatim.
5. Return the reassembled bytes.

Coverage
--------
Implemented (round-trips through parse_yamaha_rivage):
* channel names (Label.Name, 64 bytes, null-padded)
* channel colors (Label.Color, 8 bytes, null-padded string)
* HPF enable + frequency
* EQ bands 1-4 (bypass flag, freq uint32 ÷10, gain int16 ÷100, Q uint16 ÷1000)
* gate enable + threshold + attack + hold + decay
* compressor enable + threshold + attack + release + ratio

Not written (calibration gap):
* compressor.makeup_gain — offset not calibrated on the parse side; writer
  emits template default bytes (matches parser behaviour, which returns 0.0).

Channels beyond N_CHANNELS (144) in the source ShowFile are silently
dropped (the RIVAGE template only allocates 144 input channel records).
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
# Real RIVAGE PM Editor regenerates this on every save; copying the
# template's value causes "couldn't access file" rejection in Editor.
# See engine/writers/yamaha_dm7.py for the forensic diff that confirmed
# this across the Yamaha MBDF family.
_UUID_OFFSET = 0x38
_UUID_LENGTH = 16

# ---------------------------------------------------------------------------
# MBDF container constants (shared with DM7/TF parsers)
# ---------------------------------------------------------------------------

OUTER_MAGIC        = b"#YAMAHA "
MMSXLIT_MAGIC      = b"MMSXLIT\x00"
MMSXLIT_HEADER_SIZE = 88
SCHEMA_SIZE_OFFSET  = 80

# ---------------------------------------------------------------------------
# RIVAGE record layout constants (mirrors parsers/yamaha_rivage.py)
# ---------------------------------------------------------------------------

RECORD_SIZE = 1890
N_CHANNELS  = 144

NAME_OFFSET,  NAME_LEN  = 10, 64
COLOR_OFFSET, COLOR_LEN = 74,  8

HPF_ON_OFFSET   = 152
HPF_FREQ_OFFSET = 153          # uint32 LE, value × 10 = Hz

EQ_BAND_START = 193
EQ_BAND_SIZE  = 9              # bypass(1) + freq_u32(4) + gain_i16(2) + Q_u16(2)
N_EQ_BANDS    = 4

GATE_ON_OFFSET        = 294
GATE_THRESHOLD_OFFSET = 409   # int16 LE, value ÷ 100 = dBFS
GATE_ATTACK_OFFSET    = 411   # uint8, ms
GATE_HOLD_OFFSET      = 414   # uint32 LE, µs
GATE_DECAY_OFFSET     = 418   # uint32 LE, µs  → Gate.release

COMP_ON_OFFSET        = 690
COMP_THRESHOLD_OFFSET = 767   # int16 LE, value ÷ 100 = dBFS
COMP_ATTACK_OFFSET    = 769   # uint16 LE, µs  → Compressor.attack (ms)
COMP_RELEASE_OFFSET   = 773   # uint16 LE, ÷ 10 = ms
COMP_RATIO_OFFSET     = 775   # uint16 LE, ÷ 100 = ratio

# ---------------------------------------------------------------------------
# Color encoding (inverse of parsers.yamaha_rivage._COLOR_MAP)
# ---------------------------------------------------------------------------

_COLOR_TO_STR: dict[ChannelColor, str] = {
    ChannelColor.BLUE:   "Blue",
    ChannelColor.RED:    "Red",
    ChannelColor.GREEN:  "Green",
    ChannelColor.YELLOW: "Yellow",
    ChannelColor.PURPLE: "Purple",
    ChannelColor.CYAN:   "Cyan",
    ChannelColor.WHITE:  "White",
    ChannelColor.OFF:    "Blue",   # No OFF in RIVAGE palette; default to Blue
}

# ---------------------------------------------------------------------------
# Template loading + MBDF decompress/recompress helpers
# ---------------------------------------------------------------------------

TEMPLATE_PATH = Path(__file__).parent / "templates" / "rivage_empty.RIVAGEPM"
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
    preserved verbatim in the output (RIVAGE files carry additional sections
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
    # Match the real Yamaha RIVAGE PM Editor output: the template's zlib
    # header is 0x78 0x01 (level 1). See yamaha_tf.py for details on why
    # recompression level matters for Editor acceptance.
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
    """Patch all supported fields of one RIVAGE InputChannel record."""
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
        freq_raw = max(0, round(band.frequency * 10))
        struct.pack_into("<I", rec, base + 1, freq_raw)
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

    # --- Compressor (makeup_gain intentionally skipped — not calibrated) ---
    comp = channel.compressor
    if comp is not None:
        rec[COMP_ON_OFFSET] = 1 if comp.enabled else 0
        thresh_raw = max(-32768, min(32767, round(comp.threshold * 100)))
        struct.pack_into("<h", rec, COMP_THRESHOLD_OFFSET, thresh_raw)
        atk_us = max(0, min(65535, round(comp.attack * 1000)))
        struct.pack_into("<H", rec, COMP_ATTACK_OFFSET, atk_us)
        rel_raw = max(0, min(65535, round(comp.release * 10)))
        struct.pack_into("<H", rec, COMP_RELEASE_OFFSET, rel_raw)
        ratio_raw = max(0, min(65535, round(comp.ratio * 100)))
        struct.pack_into("<H", rec, COMP_RATIO_OFFSET, ratio_raw)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Pre-compute template decomposition once at import time so each call only
# pays for patching + re-compression, not the full scan/decompress overhead.
_ZLIB_OFFSET  = _find_zlib_offset(_TEMPLATE_BYTES)
_INNER_BYTES, _TRAILING_BYTES = _decompress_inner(_TEMPLATE_BYTES, _ZLIB_OFFSET)
_DATA_START   = _find_data_start(_INNER_BYTES)
_OUTER_HEADER = _TEMPLATE_BYTES[:_ZLIB_OFFSET]


def write_yamaha_rivage(show: ShowFile) -> bytes:
    """Render *show* into a Yamaha RIVAGE PM .RIVAGEPM binary file.

    The empty RIVAGE template is decomposed once at module import time.
    Each call gets a fresh ``bytearray`` copy of the inner blob, patches
    the channel records, re-compresses, and splices back into the outer
    container.

    Channels beyond ``N_CHANNELS`` (144) are silently dropped.

    Parameters
    ----------
    show : ShowFile
        Universal model populated by any source-format parser.

    Returns
    -------
    bytes
        Valid .RIVAGEPM binary, loadable by the RIVAGE parser.
    """
    # Fresh mutable copy of the decompressed inner blob.
    inner = bytearray(_INNER_BYTES)

    written = 0
    for ch_idx, channel in enumerate(show.channels):
        if ch_idx >= N_CHANNELS:
            logger.warning(
                "write_yamaha_rivage: channel %d beyond limit (%d); skipping",
                ch_idx + 1, N_CHANNELS,
            )
            break

        rec_off = _DATA_START + ch_idx * RECORD_SIZE
        if rec_off + RECORD_SIZE > len(inner):
            logger.warning(
                "write_yamaha_rivage: template too small for channel %d; stopping",
                ch_idx + 1,
            )
            break

        rec = bytearray(inner[rec_off : rec_off + RECORD_SIZE])
        _patch_channel(rec, channel)
        inner[rec_off : rec_off + RECORD_SIZE] = rec
        written += 1

    logger.info("write_yamaha_rivage: patched %d channels", written)

    new_zlib = _recompress(bytes(inner))

    # Regenerate the per-save UUID in the outer header so Editor accepts.
    outer = bytearray(_OUTER_HEADER)
    outer[_UUID_OFFSET:_UUID_OFFSET + _UUID_LENGTH] = uuid.uuid4().bytes

    return bytes(outer) + new_zlib + _TRAILING_BYTES


__all__ = ["write_yamaha_rivage"]
