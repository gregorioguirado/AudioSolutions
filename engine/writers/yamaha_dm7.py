"""Template-based writer for Yamaha DM7 binary .dm7f show files.

Strategy
--------
Load an empty DM7 template once at module import time.
For each ``write_yamaha_dm7`` call:

1. Create a fresh ``bytearray`` copy of the template (template is never
   mutated across calls).
2. Locate the first ``#YAMAHA MBDFBackup`` zlib blob — this is the
   CurrentBackupFile section that holds the Mixing data (InputChannel records).
3. Decompress the blob, patch the 1785-byte channel records at the same
   offsets the parser reads from, then re-compress.
4. Splice the re-compressed blob back into the file buffer (same header prefix,
   same trailing sections).  The .bup.old pair and all other sections
   (SetupBackupFile, PresetListBackupFile, SceneListBackupFile) are preserved
   unchanged from the template.

Coverage
--------
Implemented (round-trips through yamaha_dm7.parse):
* Channel names (NAME_OFFSET, 64 bytes, null-padded UTF-8)
* Channel colors (COLOR_OFFSET, 8 bytes, string label)
* HPF enable + frequency (HPF_ON_OFFSET, HPF_FREQ_OFFSET; freq in 0.1 Hz units)
* Phase invert (PHASE_OFFSET)
* DCA assignments (DCA_OFFSET, 3-byte little-endian bitmask)
* Mute group assignments (MUTE_GRP_OFFSET, 2-byte little-endian bitmask)
* EQ: 4-band per-channel (active bank only; freq, gain, Q, bypass, shelf bits)
* Gate: On flag + threshold + attack + hold + release (GATE type only)
* Compressor: On flag + threshold + ratio + attack + release + makeup_gain
  (Classic Comp layout — the only fully calibrated comp type)

NOT written (parser reads these as defaults or doesn't expose them):
* FADER_OFFSET (1772) — universal model has no fader field; template default kept
* HPF Slope byte (HPF_SLOPE_OFFSET 139) — template default (12 dB/oct) kept
* Mix bus assignments (ToMix offsets not yet mapped in parser)
* Channel mute/On flag (offset not yet mapped in parser)
* VirtualSC, Insert, DirectOut sections — not parsed
"""
from __future__ import annotations

import logging
import re
import struct
import zlib
from pathlib import Path

from models.universal import Channel, ChannelColor, ShowFile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

TEMPLATE_PATH = Path(__file__).parent / "templates" / "dm7_empty.dm7f"
_TEMPLATE_BYTES: bytes = TEMPLATE_PATH.read_bytes()

# ---------------------------------------------------------------------------
# MBDF / record constants (must match parsers/yamaha_dm7.py)
# ---------------------------------------------------------------------------

OUTER_MAGIC   = b"#YAMAHA "
INNER_MAGIC   = b"#YAMAHA MBDFBackup"
MMSXLIT_MAGIC = b"MMSXLIT\x00"

MMSXLIT_HEADER_SIZE = 88
SCHEMA_SIZE_OFFSET  = 80   # relative to MMSXLIT magic

RECORD_SIZE  = 1785
MAX_CHANNELS = 120

# Offsets within a 1785-byte InputChannel record
NAME_OFFSET      = 10
COLOR_OFFSET     = 74
HPF_ON_OFFSET    = 134
HPF_FREQ_OFFSET  = 135
HPF_SLOPE_OFFSET = 139
PHASE_OFFSET     = 108
DCA_OFFSET       = 1767
MUTE_GRP_OFFSET  = 1770

NAME_LEN  = 64
COLOR_LEN = 8

# PEQ layout
PEQ_OFFSET       = 182
PEQ_ACTOR_OFFSET = PEQ_OFFSET + 1
PEQ_BANK_0       = PEQ_OFFSET + 2
PEQ_BANK_SIZE    = 73

_PB_ON         = 0
_PB_TYPE       = 1
_PB_ATT        = 13
_PB_BAND_FIRST = 15
_PB_BAND_SIZE  = 9
_PB_LOWSHELF   = 51
_PB_HIGHSHELF  = 54

_BD_BYPASS = 0
_BD_FREQ   = 1
_BD_GAIN   = 5
_BD_Q      = 7

# Dynamics layout
DYN_OFFSET    = 477
DYN_SIZE      = 422
DYN_BANK_SIZE = 74

_DB_ON    = 0
_DB_TYPE  = 1
_DB_PARAM = 18

# ---------------------------------------------------------------------------
# Color mapping (inverse of parsers/yamaha_dm7.py _COLOR_MAP)
# ---------------------------------------------------------------------------

_COLOR_TO_STR: dict[ChannelColor, str] = {
    ChannelColor.BLUE:   "Blue",
    ChannelColor.RED:    "Red",
    ChannelColor.GREEN:  "Green",
    ChannelColor.YELLOW: "Yellow",
    ChannelColor.PURPLE: "Purple",
    ChannelColor.CYAN:   "Cyan",
    ChannelColor.WHITE:  "White",
    ChannelColor.OFF:    "Blue",   # no OFF in DM7 — fall back to default Blue
}


def _encode_str(value: str, length: int) -> bytes:
    """Encode a string into a fixed-length null-padded UTF-8 field."""
    raw = value.encode("utf-8", errors="replace")[:length]
    return raw.ljust(length, b"\x00")


_INT32_MAX = 2_147_483_647
_INT32_MIN = -2_147_483_648


def _clamp_i32(value: int) -> int:
    """Clamp *value* to the signed 32-bit integer range for struct.pack_into '<i'."""
    return max(_INT32_MIN, min(_INT32_MAX, value))


# ---------------------------------------------------------------------------
# Outer container: locate, decompress, splice
# ---------------------------------------------------------------------------

def _find_first_mbdf_blob(data: bytes) -> tuple[int, int]:
    """Return (blob_start, compressed_length) of the first valid MBDF zlib blob.

    Searches from offset 40 (past the outer file header) for a zlib magic byte
    whose decompressed content starts with the YAMAHA MBDF magic.  Returns the
    exact compressed byte length so the caller can splice cleanly.
    """
    for m in re.finditer(rb"\x78[\x01\x5e\x9c\xda]", data[40:]):
        pos = m.start() + 40
        try:
            inner = zlib.decompress(data[pos:])
            if not inner.startswith(OUTER_MAGIC):
                continue
            # Measure exact compressed length via unused_data
            d = zlib.decompressobj()
            d.decompress(data[pos:])
            compressed_len = len(data) - pos - len(d.unused_data)
            return pos, compressed_len
        except zlib.error:
            continue
    raise ValueError("No valid #YAMAHA MBDFBackup blob found in template")


def _find_data_start(inner: bytes) -> int:
    """Return the byte offset of the first InputChannel record in *inner*."""
    mmsxlit_pos = inner.index(MMSXLIT_MAGIC)
    schema_size = struct.unpack_from("<I", inner, mmsxlit_pos + SCHEMA_SIZE_OFFSET)[0]
    return mmsxlit_pos + MMSXLIT_HEADER_SIZE + schema_size


# ---------------------------------------------------------------------------
# Per-field patch helpers (write into the decompressed inner bytearray)
# ---------------------------------------------------------------------------

def _patch_name(buf: bytearray, rec_base: int, name: str) -> None:
    raw = _encode_str(name, NAME_LEN)
    buf[rec_base + NAME_OFFSET : rec_base + NAME_OFFSET + NAME_LEN] = raw


def _patch_color(buf: bytearray, rec_base: int, color: ChannelColor) -> None:
    label = _COLOR_TO_STR.get(color, "Blue")
    raw = _encode_str(label, COLOR_LEN)
    buf[rec_base + COLOR_OFFSET : rec_base + COLOR_OFFSET + COLOR_LEN] = raw


def _patch_hpf(buf: bytearray, rec_base: int, freq_hz: float, enabled: bool) -> None:
    buf[rec_base + HPF_ON_OFFSET] = 0x01 if enabled else 0x00
    freq_raw = max(0, min(0xFFFFFFFF, round(freq_hz * 10.0)))
    struct.pack_into("<I", buf, rec_base + HPF_FREQ_OFFSET, freq_raw)
    # Slope kept at template default (12 dB/oct)


def _patch_phase(buf: bytearray, rec_base: int, phase: bool) -> None:
    buf[rec_base + PHASE_OFFSET] = 0x01 if phase else 0x00


def _patch_dca(buf: bytearray, rec_base: int, vca_assignments: list[int]) -> None:
    mask = 0
    for dca in vca_assignments:
        idx = dca - 1  # 1-indexed → 0-indexed
        if 0 <= idx < 24:
            mask |= (1 << idx)
    buf[rec_base + DCA_OFFSET]     = (mask >> 0)  & 0xFF
    buf[rec_base + DCA_OFFSET + 1] = (mask >> 8)  & 0xFF
    buf[rec_base + DCA_OFFSET + 2] = (mask >> 16) & 0xFF


def _patch_mute_groups(buf: bytearray, rec_base: int, mute_groups: list[int]) -> None:
    mask = 0
    for g in mute_groups:
        idx = g - 1
        if 0 <= idx < 12:
            mask |= (1 << idx)
    buf[rec_base + MUTE_GRP_OFFSET]     = (mask >> 0) & 0xFF
    buf[rec_base + MUTE_GRP_OFFSET + 1] = (mask >> 8) & 0xFF


def _patch_eq(buf: bytearray, rec_base: int, channel: Channel) -> None:
    """Patch EQ bands into the active bank (bank 0).

    We always write into bank 0 and set actor (active bank index) to 0.
    The four EQ band types are encoded as low-shelf/high-shelf bit flags.
    """
    from models.universal import EQBandType

    bands = channel.eq_bands
    if not bands:
        return

    # Set active bank to 0
    buf[rec_base + PEQ_ACTOR_OFFSET] = 0x00
    bank_base = rec_base + PEQ_BANK_0  # bank 0

    for i, band in enumerate(bands[:4]):
        off = bank_base + _PB_BAND_FIRST + i * _PB_BAND_SIZE

        # Bypass bit (enabled → not bypassed)
        buf[off + _BD_BYPASS] = 0x00 if band.enabled else 0x01

        # Frequency: uint32_t in 0.1 Hz units
        freq_raw = max(0, min(0xFFFFFFFF, round(band.frequency * 10.0)))
        struct.pack_into("<I", buf, off + _BD_FREQ, freq_raw)

        # Gain: int16_t in 0.01 dB units
        gain_raw = max(-32768, min(32767, round(band.gain * 100.0)))
        struct.pack_into("<h", buf, off + _BD_GAIN, gain_raw)

        # Q: uint16_t in 0.001 units
        q_raw = max(0, min(65535, round(band.q * 1000.0)))
        struct.pack_into("<H", buf, off + _BD_Q, q_raw)

    # Shelf type bits: band[0] = LOW_SHELF → set _PB_LOWSHELF bit
    #                  band[3] = HIGH_SHELF → set _PB_HIGHSHELF bit
    if len(bands) >= 1:
        buf[bank_base + _PB_LOWSHELF] = (
            0x01 if bands[0].band_type == EQBandType.LOW_SHELF else 0x00
        )
    if len(bands) >= 4:
        buf[bank_base + _PB_HIGHSHELF] = (
            0x01 if bands[3].band_type == EQBandType.HIGH_SHELF else 0x00
        )


def _patch_gate(buf: bytearray, rec_base: int, channel: Channel) -> None:
    """Patch Dynamics[0] (Gate slot) using Classic GATE layout."""
    gate = channel.gate

    # Dynamics unit 0 base in record
    dyn_base = rec_base + DYN_OFFSET
    # actor = 0 → bank 0
    buf[dyn_base + 1] = 0x00
    bank_base = dyn_base + 2  # bank 0

    if gate is None or not gate.enabled:
        buf[bank_base + _DB_ON] = 0x00
        return

    buf[bank_base + _DB_ON] = 0x01

    # Type string: "GATE" (16 bytes null-padded)
    type_raw = _encode_str("GATE", 16)
    buf[bank_base + _DB_TYPE : bank_base + _DB_TYPE + 16] = type_raw

    # Parameters (10 × int32_t):
    # P[0]: threshold × 100 → int (0.01 dB units)
    # P[1]: attack in ms (direct integer)
    # P[3]: hold in µs (ms × 1000)
    # P[4]: release in µs (ms × 1000)
    params = [0] * 10
    params[0] = _clamp_i32(round(gate.threshold * 100.0))
    params[1] = _clamp_i32(round(gate.attack))
    params[3] = _clamp_i32(round(gate.hold * 1000.0))
    params[4] = _clamp_i32(round(gate.release * 1000.0))

    for idx, val in enumerate(params):
        struct.pack_into("<i", buf, bank_base + _DB_PARAM + idx * 4, val)


def _patch_compressor(buf: bytearray, rec_base: int, channel: Channel) -> None:
    """Patch Dynamics[1] (Comp slot) using Classic Comp layout."""
    comp = channel.compressor

    # Dynamics unit 1 base in record
    dyn_base = rec_base + DYN_OFFSET + DYN_SIZE
    buf[dyn_base + 1] = 0x00  # actor = 0 → bank 0
    bank_base = dyn_base + 2

    if comp is None or not comp.enabled:
        buf[bank_base + _DB_ON] = 0x00
        return

    buf[bank_base + _DB_ON] = 0x01

    # Type string: "Classic Comp" (16 bytes null-padded)
    type_raw = _encode_str("Classic Comp", 16)
    buf[bank_base + _DB_TYPE : bank_base + _DB_TYPE + 16] = type_raw

    # Parameters:
    # P[0]: threshold × 100 (0.01 dB units)
    # P[1]: attack in µs (ms × 1000)
    # P[2]: release in 0.1 ms units (ms × 10)
    # P[3]: ratio × 100 (e.g. 440 for 4.4:1)
    # P[5]: makeup_gain × 100 (0.01 dB units)
    params = [0] * 10
    params[0] = _clamp_i32(round(comp.threshold * 100.0))
    params[1] = _clamp_i32(round(comp.attack * 1000.0))
    params[2] = _clamp_i32(round(comp.release * 10.0))
    params[3] = _clamp_i32(round(comp.ratio * 100.0))
    params[5] = _clamp_i32(round(comp.makeup_gain * 100.0))

    for idx, val in enumerate(params):
        struct.pack_into("<i", buf, bank_base + _DB_PARAM + idx * 4, val)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def write_yamaha_dm7(show: ShowFile) -> bytes:
    """Render *show* into a Yamaha DM7 .dm7f binary file.

    The empty DM7 template is loaded once at module import time.  A fresh
    copy is made for each call so the template is never mutated.

    Channels beyond ``MAX_CHANNELS`` (120) are silently dropped — the DM7
    console addresses 120 input channels in the Mixing section.

    Parameters
    ----------
    show : ShowFile
        Universal model populated by any source-format parser.

    Returns
    -------
    bytes
        A valid .dm7f file that can be re-parsed by ``parsers.yamaha_dm7.parse``.
    """
    template = bytearray(_TEMPLATE_BYTES)

    # Step 1: Locate the first MBDF blob (CurrentBackupFile.bup = Mixing data)
    blob_start, blob_len = _find_first_mbdf_blob(bytes(template))

    # Step 2: Decompress the inner blob
    inner = bytearray(zlib.decompress(template[blob_start : blob_start + blob_len]))

    # Step 3: Find the InputChannel data section within the inner blob
    data_start = _find_data_start(inner)

    # Step 4: Patch each channel record
    written = 0
    for ch_idx, channel in enumerate(show.channels):
        if ch_idx >= MAX_CHANNELS:
            break
        rec_base = data_start + ch_idx * RECORD_SIZE
        if rec_base + RECORD_SIZE > len(inner):
            logger.warning("DM7 writer: channel %d record exceeds inner blob bounds — skipping", ch_idx)
            break

        _patch_name(inner, rec_base, channel.name)
        _patch_color(inner, rec_base, channel.color)
        _patch_hpf(inner, rec_base, channel.hpf_frequency, channel.hpf_enabled)
        _patch_phase(inner, rec_base, getattr(channel, "phase_invert", False))
        _patch_dca(inner, rec_base, channel.vca_assignments)
        _patch_eq(inner, rec_base, channel)
        _patch_gate(inner, rec_base, channel)
        _patch_compressor(inner, rec_base, channel)
        written += 1

    # Step 5: Re-compress matching the template's compression level (1).
    # Yamaha Editor apps appear to tie acceptance to the exact compressed
    # byte stream; mismatched levels produce valid zlib output that our own
    # parser accepts but the Editor rejects. See yamaha_tf.py for details.
    new_blob = zlib.compress(bytes(inner), level=1)

    # Step 6: Splice: header | new_blob | original_tail
    header  = bytes(template[:blob_start])
    tail    = bytes(template[blob_start + blob_len:])
    result  = header + new_blob + tail

    logger.info(
        "write_yamaha_dm7: wrote %d channels; blob %d→%d bytes (%+d)",
        written, blob_len, len(new_blob), len(new_blob) - blob_len,
    )
    return result


__all__ = ["write_yamaha_dm7"]
