"""Template-based writer for real Yamaha CL/QL binary .CLF show files.

Strategy
--------
Load an empty CL5 calibration template once at module import time.
For each ``write_yamaha_cl_binary`` call:

1. Create a fresh ``bytearray`` copy of the template (so the in-memory
   template is never mutated across calls).
2. Locate the best MEMAPI scene marker in the copy via the same
   ``_pick_best_scene`` heuristic the parser uses.
3. Overwrite parameter bytes at the same MEMAPI-relative offsets the
   parser reads from.  The conversion helpers in this module are the
   inverse of the parser's helpers (semitone scale for EQ, log scales
   for HPF / comp release / gate hold / comp ratio, etc.).
4. Return the modified bytes.

Coverage
--------
Implemented (round-trips through parse_yamaha_cl_binary):
* channel names (NAME_TABLE_1 + NAME_TABLE_2)
* channel colors (COLOR_TABLE)
* HPF enable + frequency
* EQ band frequency + gain (4 bands)
* gate enable + threshold + attack
* compressor enable + threshold + attack + release + ratio + makeup
* channel mute (CHANNEL_OFF)
* DCA assignments (8 DCAs)
* fader / pan default bytes (universal model carries no fader/pan field
  yet, so the writer emits sane defaults to keep the file well-formed)

TODOs (left intentionally for later passes):
* Gate hold / decay / range — parser uses a log scale we can invert,
  but the universal model carries only ``release`` and we have no decay
  field to round-trip cleanly. Defaults preserved from template.
* Mix bus sends — 5184-byte block per scene; not modelled in the
  universal Channel yet.
* Mute groups — not in the universal model.
* EQ Q values for bands 3-4 — Q offsets not yet mapped in the parser.
* Channel-OFF flag has the same range constraint as the parser
  (1-byte 0/1).  Threshold encoding inherits the parser's fixed
  high-byte assumption (0xFE for gate, 0xFF for comp).
"""
from __future__ import annotations

import logging
import math
import struct
from pathlib import Path

from models.universal import Channel, ChannelColor, ShowFile
from parsers.yamaha_cl_binary import (
    CHANNEL_OFF_REL,
    COLOR_TABLE_REL,
    COMP_ATTACK_REL,
    COMP_ENABLE_REL,
    COMP_MAKEUP_REL,
    COMP_RATIO_REL,
    COMP_RELEASE_REL,
    COMP_THRESHOLD_REL,
    DCA_BASE_REL,
    DCA_STRIDE,
    EQ_BAND_BASES_REL,
    EQ_PREFIX_BYTES,
    FADER_REL,
    GATE_ATTACK_REL,
    GATE_DECAY_REL,
    GATE_ENABLE_REL,
    GATE_HOLD_REL,
    GATE_THRESHOLD_REL,
    HPF_ENABLE_REL,
    HPF_FREQ_REL,
    NAME_TABLE_1_REL,
    NAME_TABLE_2_REL,
    NUM_INPUT_CHANNELS,
    PAN_REL,
    _find_all_memapi,
    _pick_best_scene,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

TEMPLATE_PATH = Path(__file__).parent / "templates" / "cl5_empty.CLF"
_TEMPLATE_BYTES: bytes = TEMPLATE_PATH.read_bytes()

# Defaults for fields the universal model does not currently carry.
DEFAULT_FADER_VALUE = 0          # -inf dB (safe, prevents accidental output)
DEFAULT_PAN_VALUE = 0            # center


# ---------------------------------------------------------------------------
# Inverse conversion helpers (match parsers.yamaha_cl_binary)
# ---------------------------------------------------------------------------

def _hpf_freq_to_byte(freq_hz: float) -> int:
    """Inverse of parser._hpf_freq.  freq = 20 * 2^((val-28)/4.8)."""
    if freq_hz <= 0:
        return 28
    val = 28 + 4.8 * math.log2(freq_hz / 20.0)
    return _clamp_byte(round(val))


def _eq_freq_to_byte(freq_hz: float) -> int:
    """Inverse of parser._eq_freq.  freq = 20 * 2^((val-4)/12)."""
    if freq_hz <= 0:
        return 4
    val = 4 + 12.0 * math.log2(freq_hz / 20.0)
    return _clamp_byte(round(val))


def _gate_hold_to_byte(hold_ms: float) -> int:
    """Inverse of parser._gate_hold.  hold = 2.33 * 2^((val-200)/3.60)."""
    if hold_ms <= 0:
        return 200
    val = 200 + 3.60 * math.log2(hold_ms / 2.33)
    return _clamp_byte(round(val))


def _comp_release_to_byte(release_ms: float) -> int:
    """Inverse of parser._comp_release.  release = 46.5 * 2^(val/16.1)."""
    if release_ms <= 0:
        return 0
    val = 16.1 * math.log2(release_ms / 46.5)
    return _clamp_byte(round(val))


def _comp_ratio_to_byte(ratio: float) -> int:
    """Inverse of parser._comp_ratio.  ratio = 2^(val/4.4)."""
    if ratio <= 1.0:
        return 0
    val = 4.4 * math.log2(ratio)
    return _clamp_byte(round(val))


def _clamp_byte(val: int) -> int:
    return max(0, min(255, int(val)))


def _encode_threshold(db: float, high_byte: int) -> int:
    """Encode a threshold dB value as the val_byte under a fixed high_byte.

    Layout in the file is ``[val_byte][high_byte]`` and the parser
    reconstructs ``signed16(high_byte << 8 | val_byte) / 10`` dB.
    For a fixed *high_byte*, the representable range is the slice of
    signed-16 values whose top 8 bits equal *high_byte*.  Values outside
    that range get clamped to the nearest representable threshold.
    """
    target = round(db * 10.0)
    # Range of signed16 values with the requested high byte:
    if high_byte & 0x80:
        # Negative half of signed16
        signed_high_byte = high_byte - 0x100
        lo = signed_high_byte * 256
        hi = signed_high_byte * 256 + 255
    else:
        lo = high_byte * 256
        hi = high_byte * 256 + 255
    target = max(lo, min(hi, target))
    raw = struct.unpack(">H", struct.pack(">h", target))[0]
    return raw & 0xFF


# ---------------------------------------------------------------------------
# Color encoding (inverse of parsers._COLOR_MAP)
# ---------------------------------------------------------------------------

_COLOR_TO_BYTE: dict[ChannelColor, int] = {
    ChannelColor.OFF: 0x00,
    ChannelColor.RED: 0x01,
    ChannelColor.GREEN: 0x02,
    ChannelColor.YELLOW: 0x03,
    ChannelColor.BLUE: 0x04,
    ChannelColor.PURPLE: 0x05,
    ChannelColor.CYAN: 0x06,
    ChannelColor.WHITE: 0x07,
}


# ---------------------------------------------------------------------------
# Per-parameter writers
# ---------------------------------------------------------------------------

def _write_name(buf: bytearray, scene: int, ch: int, name: str) -> None:
    """Split *name* into two 4-byte halves and write at NAME_TABLE_1/2."""
    encoded = (name or "").encode("ascii", errors="replace")[:8]
    encoded = encoded.ljust(8, b"\x00")
    part1, part2 = encoded[:4], encoded[4:8]
    off1 = scene + NAME_TABLE_1_REL + ch * 4
    off2 = scene + NAME_TABLE_2_REL + ch * 4
    buf[off1:off1 + 4] = part1
    buf[off2:off2 + 4] = part2


def _write_color(buf: bytearray, scene: int, ch: int, color: ChannelColor) -> None:
    val = _COLOR_TO_BYTE.get(color, 0x07)  # default WHITE
    buf[scene + COLOR_TABLE_REL + ch] = val


def _write_hpf(buf: bytearray, scene: int, ch: int,
               freq_hz: float, enabled: bool) -> None:
    """Write HPF state for one channel.

    Caveat: the parser's HPF_ENABLE_REL block is only 12 bytes long; for
    channels 12-71 the parser reads the *frequency* byte of channel
    (ch - 12) as the enable flag.  We therefore only write a true enable
    byte for ch < 12; for ch >= 12, the channel will read back as enabled
    iff its freq byte is non-zero (which is true for any freq >= 20 Hz).
    """
    if ch < 12:
        buf[scene + HPF_ENABLE_REL + ch] = 1 if enabled else 0
    buf[scene + HPF_FREQ_REL + ch] = _hpf_freq_to_byte(freq_hz)


def _write_mute(buf: bytearray, scene: int, ch: int, muted: bool) -> None:
    buf[scene + CHANNEL_OFF_REL + ch] = 1 if muted else 0


def _write_fader_pan_defaults(buf: bytearray, scene: int, ch: int) -> None:
    """Universal model has no fader/pan field yet — write safe defaults."""
    fader_off = scene + FADER_REL + ch * 2
    buf[fader_off:fader_off + 2] = struct.pack(">H", DEFAULT_FADER_VALUE)
    pan_off = scene + PAN_REL + ch
    buf[pan_off] = DEFAULT_PAN_VALUE & 0xFF


def _write_gate(buf: bytearray, scene: int, ch: int, channel: Channel) -> None:
    gate = channel.gate
    if gate is None:
        buf[scene + GATE_ENABLE_REL + ch] = 0
        return
    buf[scene + GATE_ENABLE_REL + ch] = 1 if gate.enabled else 0
    buf[scene + GATE_ATTACK_REL + ch] = _clamp_byte(round(gate.attack))
    # Hold: inverse of parser's _gate_hold log scale.
    buf[scene + GATE_HOLD_REL + ch] = _gate_hold_to_byte(gate.hold)
    # Decay (parser maps raw byte directly to Gate.release in ms).
    buf[scene + GATE_DECAY_REL + ch] = _clamp_byte(round(gate.release))
    # Threshold: 2-byte stride [val][0xFE].
    th_off = scene + GATE_THRESHOLD_REL + ch * 2
    buf[th_off] = _encode_threshold(gate.threshold, 0xFE)
    buf[th_off + 1] = 0xFE


def _write_compressor(buf: bytearray, scene: int, ch: int, channel: Channel) -> None:
    comp = channel.compressor
    if comp is None:
        buf[scene + COMP_ENABLE_REL + ch] = 0
        return
    buf[scene + COMP_ENABLE_REL + ch] = 1 if comp.enabled else 0
    buf[scene + COMP_ATTACK_REL + ch] = _clamp_byte(round(comp.attack))
    buf[scene + COMP_RELEASE_REL + ch] = _comp_release_to_byte(comp.release)
    buf[scene + COMP_RATIO_REL + ch] = _comp_ratio_to_byte(comp.ratio)
    buf[scene + COMP_MAKEUP_REL + ch] = _clamp_byte(round(comp.makeup_gain * 10))
    th_off = scene + COMP_THRESHOLD_REL + ch * 2
    buf[th_off] = _encode_threshold(comp.threshold, 0xFF)
    buf[th_off + 1] = 0xFF


def _write_eq(buf: bytearray, scene: int, ch: int, channel: Channel) -> None:
    """Write 4 EQ bands (frequency byte + 2-byte signed BE gain).

    Q values are not written — band-3/4 Q offsets aren't mapped in the parser.
    """
    bands = channel.eq_bands
    if not bands:
        return
    for band_idx, band in enumerate(bands[:4]):
        band_base = scene + EQ_BAND_BASES_REL[band_idx]
        prefix = EQ_PREFIX_BYTES[band_idx]
        # Frequency: 1B in table 1 (+96)
        freq_off = band_base + 96 + prefix + ch
        buf[freq_off] = _eq_freq_to_byte(band.frequency)
        # Gain: 2B signed BE in table 2 (+192)
        gain_off = band_base + 192 + prefix + ch * 2
        gain_raw = max(-32768, min(32767, round(band.gain * 10)))
        buf[gain_off:gain_off + 2] = struct.pack(">h", gain_raw)


def _write_dcas(buf: bytearray, scene: int, ch: int, channel: Channel) -> None:
    """Write DCA assignments (8 DCAs, stride 12, 1 byte per channel)."""
    for dca_idx in range(8):
        offset = scene + DCA_BASE_REL + dca_idx * DCA_STRIDE + ch
        # vca_assignments are 1-indexed
        buf[offset] = 1 if (dca_idx + 1) in channel.vca_assignments else 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _raw_write(show: ShowFile) -> bytearray:
    """Uncorrected write — patches every field as-is into a fresh template copy."""
    buf = bytearray(_TEMPLATE_BYTES)

    scenes = _find_all_memapi(buf)
    if not scenes:
        raise RuntimeError(
            f"Template at {TEMPLATE_PATH} contains no MEMAPI marker"
        )
    scene = _pick_best_scene(bytes(buf), scenes)

    for ch_idx, channel in enumerate(show.channels):
        if ch_idx >= NUM_INPUT_CHANNELS:
            break
        _write_name(buf, scene, ch_idx, channel.name)
        _write_color(buf, scene, ch_idx, channel.color)
        _write_hpf(buf, scene, ch_idx, channel.hpf_frequency, channel.hpf_enabled)
        _write_mute(buf, scene, ch_idx, channel.muted)
        _write_fader_pan_defaults(buf, scene, ch_idx)
        _write_gate(buf, scene, ch_idx, channel)
        _write_compressor(buf, scene, ch_idx, channel)
        _write_eq(buf, scene, ch_idx, channel)
        _write_dcas(buf, scene, ch_idx, channel)

    return buf


def write_yamaha_cl_binary(show: ShowFile) -> bytes:
    """Render *show* into a Yamaha CL/QL .CLF binary file.

    The empty calibration template is loaded once at module import time and
    copied into a fresh ``bytearray`` for each call, so the template buffer
    is never mutated across calls.

    Channels beyond ``NUM_INPUT_CHANNELS`` (72) in *show* are silently
    dropped (the CL5 hardware can only address 72 inputs).

    A **correction map** pre-computed at import time restores any byte the
    raw writer produces as a "wrong default" (e.g. encoding the CL5's
    0x16 default colour as 0x07 because our enum doesn't know the native
    0x16 value, or writing a plain 0/1 for a flag byte whose upper bits
    the template uses for packed state). This guarantees that an unchanged
    round-trip produces a byte-identical template and that cross-format
    translations only modify bytes the source actually changed — the real
    console editor apps reject files with unexpected byte drift in
    non-channel regions.

    Parameters
    ----------
    show : ShowFile
        Universal model populated by any source-format parser.

    Returns
    -------
    bytes
        Modified template, valid as a CL5 .CLF binary.
    """
    buf = _raw_write(show)

    # Correction pass: wherever the raw writer produced the exact "wrong
    # default" byte that _BASELINE_WRITTEN has for this position, restore
    # the template's original byte. If the source genuinely changed this
    # byte to a different value, _raw_write produced something other than
    # _BASELINE_WRITTEN[off] and we leave it alone.
    for off, (template_byte, baseline_byte) in _CORRECTION_MAP.items():
        if buf[off] == baseline_byte:
            buf[off] = template_byte

    return bytes(buf)


# Pre-compute the correction map at module import time by round-tripping
# the template through the raw writer and recording every byte position
# where the raw writer's output diverges from the template.
def _compute_correction_map() -> dict[int, tuple[int, int]]:
    from parsers.yamaha_cl_binary import parse_yamaha_cl_binary
    template_show = parse_yamaha_cl_binary(TEMPLATE_PATH)
    baseline = _raw_write(template_show)
    m: dict[int, tuple[int, int]] = {}
    for i in range(len(_TEMPLATE_BYTES)):
        if baseline[i] != _TEMPLATE_BYTES[i]:
            m[i] = (_TEMPLATE_BYTES[i], baseline[i])
    return m


_CORRECTION_MAP: dict[int, tuple[int, int]] = _compute_correction_map()


__all__ = [
    "write_yamaha_cl_binary",
    "DEFAULT_FADER_VALUE",
    "DEFAULT_PAN_VALUE",
]
