"""Parser for real Yamaha CL/QL binary .CLF and .CLE show files.

Reads raw binary data using the MEMAPI-relative offset map derived from
calibration and reverse-engineering of the Yamaha CL5 format.

Supports both CLF (console USB save) and CLE (CL Editor desktop save).
"""
from __future__ import annotations

import logging
import struct
from pathlib import Path

from models.universal import (
    ShowFile, Channel, EQBand, Gate, Compressor,
    ChannelColor, EQBandType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — all offsets relative to a scene's MEMAPI marker
# ---------------------------------------------------------------------------

MEMAPI_MARKER = b"MEMAPI"

# Channel names: two tables of 96 x 4-byte entries (first 4 + last 4 chars)
NAME_TABLE_1_REL = 0x7244      # 96 entries x 4 bytes
NAME_TABLE_2_REL = 0x73C4      # 96 entries x 4 bytes (= NAME_TABLE_1 + 384)
COLOR_TABLE_REL  = 0x7544      # 96 entries x 1 byte

# Enable flags (1 byte per channel, 0=off, 1=on)
GATE_ENABLE_REL  = 0x0E84
COMP_ENABLE_REL  = 0x1460
HPF_ENABLE_REL   = 0x1A30

# HPF frequency: 1 byte per channel
HPF_FREQ_REL     = 0x1A3C

# Gate parameters
GATE_ATTACK_REL    = 0x1094   # 1B/ch, ms = value
GATE_HOLD_REL      = 0x10F4   # 1B/ch, log scale
GATE_DECAY_REL     = 0x1154   # 1B/ch, log scale
GATE_RANGE_REL     = 0x11B4   # 1B/ch
GATE_THRESHOLD_REL = 0x1335   # 2B stride [val][0xFE], signed16/10 = dB

# Compressor parameters
COMP_ATTACK_REL    = 0x1670   # 1B/ch, ms = value
COMP_RELEASE_REL   = 0x1790   # 1B/ch, log scale
COMP_RATIO_REL     = 0x17F0   # 1B/ch, ~2^(val/4.4)
COMP_MAKEUP_REL    = 0x1850   # 1B/ch, dB = value/10
COMP_KNEE_REL      = 0x18B0   # 1B/ch
COMP_THRESHOLD_REL = 0x1911   # 2B stride [val][0xFF], signed16/10 = dB

# EQ bands — base offsets relative to MEMAPI
EQ_BAND_BASES_REL = [0x1C00, 0x1D80, 0x1F00, 0x2080]
# Prefix bytes per band (non-input-channel entries before ch1)
EQ_PREFIX_BYTES   = [4, 16, 28, 40]
# Default frequency indices per band
EQ_DEFAULT_FREQ_IDX = [36, 72, 96, 112]

# Fader / Pan / Mute
PAN_REL         = 0x09C6   # 1B/ch signed
FADER_REL       = 0x0A26   # 2B/ch BE
CHANNEL_OFF_REL = 0x53FE   # 1B/ch (0=on, 1=off)

# DCA assignments — 8 DCAs, stride 12 bytes each
DCA_BASE_REL    = 0x2720
DCA_STRIDE      = 12

# Mute groups — 8 groups, stride 12 bytes each
MUTE_GROUP_BASE_REL = 0x26C0
MUTE_GROUP_STRIDE   = 12

# Number of input channels to extract
NUM_INPUT_CHANNELS = 72
# Total entries in each 96-entry table
TOTAL_TABLE_ENTRIES = 96

# Scene block size (approximate, for sanity checks)
SCENE_BLOCK_SIZE = 0xAE68


# ---------------------------------------------------------------------------
# Value conversion helpers
# ---------------------------------------------------------------------------

def _hpf_freq(val: int) -> float:
    """Convert HPF frequency byte to Hz.  20 * 2^((val-28)/4.8)"""
    return 20.0 * (2.0 ** ((val - 28) / 4.8))


def _eq_freq(val: int) -> float:
    """Convert EQ frequency byte to Hz.  20 * 2^((val-4)/12) (semitone scale)"""
    return 20.0 * (2.0 ** ((val - 4) / 12.0))


def _gate_hold(val: int) -> float:
    """Convert gate hold byte to ms.  2.33 * 2^((val-200)/3.60)"""
    return 2.33 * (2.0 ** ((val - 200) / 3.60))


def _comp_release(val: int) -> float:
    """Convert compressor release byte to ms.  46.5 * 2^(val/16.1)"""
    return 46.5 * (2.0 ** (val / 16.1))


def _comp_ratio(val: int) -> float:
    """Convert compressor ratio byte to ratio.  ~2^(val/4.4)"""
    return 2.0 ** (val / 4.4)


def _reconstruct_threshold(data: bytes, base_offset: int, ch_index: int,
                            high_byte: int) -> float:
    """Read a 2-byte-stride threshold value.

    Layout is [val_byte][high_byte] per channel (stride 2).
    Reconstructed as (high_byte << 8) | val_byte, interpreted as signed 16-bit,
    then divided by 10 to get dB.
    """
    offset = base_offset + ch_index * 2
    if offset + 1 >= len(data):
        raise IndexError(f"Threshold offset {offset} out of range")
    val_byte = data[offset]
    raw = (high_byte << 8) | val_byte
    signed = struct.unpack(">h", struct.pack(">H", raw))[0]
    return signed / 10.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_byte(data: bytes, offset: int, default: int = 0) -> int:
    """Read a single byte, returning *default* if out of range."""
    if 0 <= offset < len(data):
        return data[offset]
    return default


def _safe_bytes(data: bytes, offset: int, length: int) -> bytes:
    """Read *length* bytes, returning a zero-filled buffer if out of range."""
    if 0 <= offset and offset + length <= len(data):
        return data[offset:offset + length]
    return b"\x00" * length


def _find_all_memapi(data: bytes) -> list[int]:
    """Return file offsets of every MEMAPI marker in *data*."""
    positions: list[int] = []
    start = 0
    while True:
        idx = data.find(MEMAPI_MARKER, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + len(MEMAPI_MARKER)
    return positions


def _scene_name(data: bytes, memapi_offset: int) -> str:
    """Read the 20-byte null-padded ASCII scene name at MEMAPI+0x0C."""
    raw = _safe_bytes(data, memapi_offset + 0x0C, 20)
    return raw.split(b"\x00")[0].decode("ascii", errors="replace")


def _pick_best_scene(data: bytes, scenes: list[int]) -> int:
    """Choose the best scene offset for parameter + name extraction.

    Strategy: return the first scene whose channel names are NOT all default
    (i.e. "ch 1", "ch 2", ...).  If every scene has default names, return
    the first scene.
    """
    if len(scenes) == 1:
        return scenes[0]

    for offset in scenes:
        name_base = offset + NAME_TABLE_1_REL
        # Check first 4 channels — default names are "ch 1", "ch 2", "ch 3", "ch 4"
        has_custom = False
        for i in range(min(4, NUM_INPUT_CHANNELS)):
            chunk = _safe_bytes(data, name_base + i * 4, 4)
            text = chunk.decode("ascii", errors="replace").rstrip("\x00").strip()
            expected_default = f"ch {i+1}" if i < 9 else f"ch{i+1}"
            if text and text != expected_default:
                has_custom = True
                break
        if has_custom:
            return offset

    # All scenes have default names; use the first one
    return scenes[0]


def _read_channel_name(data: bytes, scene_offset: int, ch_index: int) -> str:
    """Combine the two 4-byte name table entries for a given channel index."""
    t1_off = scene_offset + NAME_TABLE_1_REL + ch_index * 4
    t2_off = scene_offset + NAME_TABLE_2_REL + ch_index * 4
    part1 = _safe_bytes(data, t1_off, 4).decode("ascii", errors="replace").rstrip("\x00")
    part2 = _safe_bytes(data, t2_off, 4).decode("ascii", errors="replace").rstrip("\x00")
    return (part1 + part2).strip()


# Yamaha binary color index to ChannelColor (partial mapping)
_COLOR_MAP: dict[int, ChannelColor] = {
    0x00: ChannelColor.OFF,
    0x01: ChannelColor.RED,
    0x02: ChannelColor.GREEN,
    0x03: ChannelColor.YELLOW,
    0x04: ChannelColor.BLUE,
    0x05: ChannelColor.PURPLE,
    0x06: ChannelColor.CYAN,
    0x07: ChannelColor.WHITE,
}


def _read_color(data: bytes, scene_offset: int, ch_index: int) -> ChannelColor:
    """Read the 1-byte color index and map to ChannelColor.

    The full Yamaha palette has more entries than the universal model.
    Unmapped values fall back to WHITE.
    """
    offset = scene_offset + COLOR_TABLE_REL + ch_index
    val = _safe_byte(data, offset)
    return _COLOR_MAP.get(val, ChannelColor.WHITE)


# ---------------------------------------------------------------------------
# Parameter extraction
# ---------------------------------------------------------------------------

def _extract_gate(data: bytes, scene: int, ch: int,
                  dropped: list[str]) -> Gate | None:
    """Extract gate parameters for channel *ch* (0-indexed)."""
    enabled = bool(_safe_byte(data, scene + GATE_ENABLE_REL + ch))
    try:
        threshold = _reconstruct_threshold(data, scene + GATE_THRESHOLD_REL, ch, 0xFE)
    except (IndexError, struct.error):
        dropped.append(f"ch{ch+1}: gate threshold out of range")
        threshold = -26.0  # default

    attack_ms = float(_safe_byte(data, scene + GATE_ATTACK_REL + ch))
    hold_ms = _gate_hold(_safe_byte(data, scene + GATE_HOLD_REL + ch))
    decay_val = _safe_byte(data, scene + GATE_DECAY_REL + ch)
    # Decay encoding is inverse-log; use raw value as a rough ms approximation.
    # The exact formula is not fully confirmed, so we store the raw value
    # and note the approximation.
    release_ms = float(decay_val)

    return Gate(
        threshold=threshold,
        attack=attack_ms,
        hold=hold_ms,
        release=release_ms,
        enabled=enabled,
    )


def _extract_compressor(data: bytes, scene: int, ch: int,
                         dropped: list[str]) -> Compressor | None:
    """Extract compressor parameters for channel *ch* (0-indexed)."""
    enabled = bool(_safe_byte(data, scene + COMP_ENABLE_REL + ch))
    try:
        threshold = _reconstruct_threshold(data, scene + COMP_THRESHOLD_REL, ch, 0xFF)
    except (IndexError, struct.error):
        dropped.append(f"ch{ch+1}: compressor threshold out of range")
        threshold = -8.0  # default

    attack_ms = float(_safe_byte(data, scene + COMP_ATTACK_REL + ch))
    release_ms = _comp_release(_safe_byte(data, scene + COMP_RELEASE_REL + ch))
    ratio = _comp_ratio(_safe_byte(data, scene + COMP_RATIO_REL + ch))
    makeup_db = _safe_byte(data, scene + COMP_MAKEUP_REL + ch) / 10.0

    return Compressor(
        threshold=threshold,
        ratio=ratio,
        attack=attack_ms,
        release=release_ms,
        makeup_gain=makeup_db,
        enabled=enabled,
    )


def _extract_eq(data: bytes, scene: int, ch: int,
                dropped: list[str]) -> list[EQBand]:
    """Extract 4-band EQ for channel *ch* (0-indexed)."""
    bands: list[EQBand] = []
    for band_idx in range(4):
        band_base = scene + EQ_BAND_BASES_REL[band_idx]
        prefix = EQ_PREFIX_BYTES[band_idx]

        # Frequency: 1 byte per entry in table 1 (+96)
        freq_offset = band_base + 96 + prefix + ch
        freq_val = _safe_byte(data, freq_offset, EQ_DEFAULT_FREQ_IDX[band_idx])
        freq_hz = _eq_freq(freq_val)

        # Gain: 2 bytes signed big-endian per entry in table 2 (+192)
        gain_offset = band_base + 192 + prefix + ch * 2
        gain_bytes = _safe_bytes(data, gain_offset, 2)
        try:
            gain_raw = struct.unpack(">h", gain_bytes)[0]
            gain_db = gain_raw / 10.0
        except struct.error:
            dropped.append(f"ch{ch+1}: EQ band {band_idx+1} gain unreadable")
            gain_db = 0.0

        # Q value: not reliably mapped for all bands yet
        q_val = 1.0  # default

        bands.append(EQBand(
            frequency=freq_hz,
            gain=gain_db,
            q=q_val,
            band_type=EQBandType.PEAK,
            enabled=True,
        ))

    if any(b.q == 1.0 for b in bands):
        dropped.append(f"ch{ch+1}: EQ Q values not extracted (using default Q=1.0)")

    return bands


def _extract_dca_assignments(data: bytes, scene: int, ch: int) -> list[int]:
    """Return list of 1-indexed DCA numbers this channel is assigned to."""
    dcas: list[int] = []
    for dca_idx in range(8):
        offset = scene + DCA_BASE_REL + dca_idx * DCA_STRIDE + ch
        if _safe_byte(data, offset):
            dcas.append(dca_idx + 1)
    return dcas


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_yamaha_cl_binary(filepath: Path) -> ShowFile:
    """Parse a Yamaha CL/QL .CLF or .CLE binary show file.

    Parameters
    ----------
    filepath : Path
        Path to a .CLF or .CLE file.

    Returns
    -------
    ShowFile
        Populated universal model with up to 72 input channels.

    Raises
    ------
    FileNotFoundError
        If *filepath* does not exist.
    ValueError
        If the file does not contain a valid MEMAPI marker.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    data = filepath.read_bytes()
    if len(data) < 256:
        raise ValueError(f"File too small to be a Yamaha show file: {len(data)} bytes")

    # --- Locate scenes ------------------------------------------------
    scenes = _find_all_memapi(data)
    if not scenes:
        raise ValueError("No MEMAPI scene markers found in file")

    # Pick the best scene (first with non-default channel names, else first)
    scene = _pick_best_scene(data, scenes)
    scene_name = _scene_name(data, scene)
    logger.info("Using scene '%s' at offset 0x%X", scene_name, scene)

    # Verify we have enough data after the scene marker
    if scene + SCENE_BLOCK_SIZE > len(data):
        logger.warning(
            "Scene at 0x%X may be truncated (need %d bytes, have %d)",
            scene, SCENE_BLOCK_SIZE, len(data) - scene,
        )

    # --- Build the ShowFile -------------------------------------------
    show = ShowFile(source_console="yamaha_cl")
    dropped = show.dropped_parameters

    for ch_idx in range(NUM_INPUT_CHANNELS):
        ch_num = ch_idx + 1  # 1-indexed channel number

        # Name
        name = _read_channel_name(data, scene, ch_idx)

        # Color
        color = _read_color(data, scene, ch_idx)

        # HPF
        hpf_enabled = bool(_safe_byte(data, scene + HPF_ENABLE_REL + ch_idx))
        hpf_freq_val = _safe_byte(data, scene + HPF_FREQ_REL + ch_idx, 28)
        hpf_frequency = _hpf_freq(hpf_freq_val)

        # Gate
        gate = _extract_gate(data, scene, ch_idx, dropped)

        # Compressor
        compressor = _extract_compressor(data, scene, ch_idx, dropped)

        # EQ
        eq_bands = _extract_eq(data, scene, ch_idx, dropped)

        # Muted (channel OFF flag)
        muted = bool(_safe_byte(data, scene + CHANNEL_OFF_REL + ch_idx))

        # DCA assignments
        vca_assignments = _extract_dca_assignments(data, scene, ch_idx)

        # Input patch: not stored per-scene in a reliable way yet
        input_patch = ch_num  # default: 1:1 mapping

        channel = Channel(
            id=ch_num,
            name=name,
            color=color,
            input_patch=input_patch,
            hpf_frequency=hpf_frequency,
            hpf_enabled=hpf_enabled,
            eq_bands=eq_bands,
            gate=gate,
            compressor=compressor,
            muted=muted,
            vca_assignments=vca_assignments,
        )
        show.channels.append(channel)

    # Log summary
    named = sum(1 for ch in show.channels if ch.name and not ch.name.startswith("ch"))
    hpf_on = sum(1 for ch in show.channels if ch.hpf_enabled)
    gate_on = sum(1 for ch in show.channels if ch.gate and ch.gate.enabled)
    comp_on = sum(1 for ch in show.channels if ch.compressor and ch.compressor.enabled)
    logger.info(
        "Parsed %d channels: %d named, %d HPF, %d gate, %d comp",
        len(show.channels), named, hpf_on, gate_on, comp_on,
    )

    return show
