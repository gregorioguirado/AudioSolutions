"""Probe DM7 binary offsets and verify against known default values.

Analytically derived layout (mms_Mixing.xml + empirical HPF/Name verification):

InputChannel record (1785 bytes):
  +0    GainGang+DelayGang packed (1 byte)
  +1    Signal (9 bytes: Relation uint8 + StereoInputType str8)
  +10   Label (84 bytes: Name str64 + Color str8 + Icon str12)
  +94   InPatch (9 bytes)
  +103  VirtualSC (5 bytes)
  +108  Input (3 bytes: Phase bit + Gain int16)
  +111  Insert (18 bytes)
  +129  DirectOut (5 bytes)
  +134  HPF[4] (24 bytes: 4 × (On:bit + Freq:uint32 + Slope:uint8))
  +158  LPF[4] (24 bytes: same layout)
  +182  PEQ (294 bytes)
          +0  Select bit
          +1  ActorSelect uint8
          +2  Bank[0..3] (4 × 73 bytes)
               Each bank:
                 +0  On bit
                 +1  Type string(12)
                 +13 Attenuator.Gain int16
                 +15 Band[0..3] (4 × 9 bytes)
                       +0  Bypass bit
                       +1  Frequency uint32  (÷10 → Hz, default 200=2000raw)
                       +5  Gain int16        (÷100 → dB, default 0)
                       +7  Q uint16          (÷1000, default 1400=0x0578)
                 +51 LowShelving (3 bytes: On bit + Q uint16)
                 +54 HighShelving (3 bytes: On bit + Q uint16)
                 +57 Label.Name string(16)
  +476  Proc (1 byte: EQDynOrder uint8)
  +477  Dynamics[0] (422 bytes)
          +0  Select bit
          +1  ActorSelect uint8
          +2  Bank[0..3] (4 × 74 bytes)
               Each bank:
                 +0  On bit
                 +1  Type string(16)  default="GATE" for dyn0, "Classic Comp" for dyn1
                 +17 MixBalance uint8
                 +18 Parameter[0..9] (10 × int32_t)  — meaning depends on Type
                 +58 Label.Name string(16)
          +298 KeyIn[0..3] (4 × 31 bytes)
  +899  Dynamics[1] (422 bytes — same layout, default type="Classic Comp")
"""
import struct
import sys
import zlib
import re

OUTER_MAGIC  = b"#YAMAHA "
MMSXLIT_MAGIC = b"MMSXLIT\x00"
MMSXLIT_HEADER_SIZE = 88
SCHEMA_SIZE_OFFSET  = 80
RECORD_SIZE  = 1785


def decompress_inner(data: bytes) -> bytes:
    for m in re.finditer(rb"\x78[\x01\x5e\x9c\xda]", data[40:]):
        pos = m.start() + 40
        try:
            inner = zlib.decompress(data[pos:])
            if inner.startswith(OUTER_MAGIC):
                return inner
        except zlib.error:
            continue
    raise ValueError("No valid compressed block found")


def find_data_start(inner: bytes) -> int:
    mmsxlit_pos = inner.index(MMSXLIT_MAGIC)
    schema_size = struct.unpack_from("<I", inner, mmsxlit_pos + SCHEMA_SIZE_OFFSET)[0]
    return mmsxlit_pos + MMSXLIT_HEADER_SIZE + schema_size


def read_str(data: bytes, offset: int, max_len: int) -> str:
    raw = data[offset:offset + max_len]
    return raw.split(b"\x00")[0].decode("utf-8", errors="replace")


def probe_channel(rec: bytes, ch_idx: int):
    print(f"\n=== Channel {ch_idx + 1} ===")

    name = read_str(rec, 10, 64)
    color = read_str(rec, 74, 8)
    print(f"  Name: {name!r}  Color: {color!r}")

    hpf_on   = bool(rec[134] & 0x01)
    hpf_freq = struct.unpack_from("<I", rec, 135)[0] / 10
    print(f"  HPF: {'ON' if hpf_on else 'off'}  {hpf_freq:.0f} Hz")

    # PEQ
    peq_start = 182
    actor = rec[peq_start + 1]
    print(f"  PEQ ActorSelect: {actor}")
    bank_off = peq_start + 2 + actor * 73
    bank_on  = bool(rec[bank_off] & 0x01)
    bank_type = read_str(rec, bank_off + 1, 12)
    att_gain = struct.unpack_from("<h", rec, bank_off + 13)[0] / 100
    print(f"  PEQ Bank[{actor}]: On={bank_on}  Type={bank_type!r}  Att={att_gain:+.2f}dB")
    for b in range(4):
        bd = bank_off + 15 + b * 9
        bypass  = bool(rec[bd] & 0x01)
        freq    = struct.unpack_from("<I", rec, bd + 1)[0] / 10
        gain_db = struct.unpack_from("<h", rec, bd + 5)[0] / 100
        q       = struct.unpack_from("<H", rec, bd + 7)[0] / 1000
        print(f"    Band {b+1}: {'BYP' if bypass else 'on'}  {freq:.0f}Hz  {gain_db:+.2f}dB  Q={q:.3f}")

    # Dynamics
    for d in range(2):
        dyn_start = 477 + d * 422
        actor_d   = rec[dyn_start + 1]
        bk = dyn_start + 2 + actor_d * 74
        dyn_on   = bool(rec[bk] & 0x01)
        dyn_type = read_str(rec, bk + 1, 16)
        params   = [struct.unpack_from("<i", rec, bk + 18 + i * 4)[0] for i in range(10)]
        print(f"  Dyn[{d}] Bank[{actor_d}]: On={dyn_on}  Type={dyn_type!r}")
        print(f"    Params: {params}")


def main(path: str, num_channels: int = 4):
    with open(path, "rb") as f:
        data = f.read()

    if not data.startswith(OUTER_MAGIC):
        sys.exit("Not a Yamaha MBDF file")

    inner = decompress_inner(data)
    data_start = find_data_start(inner)
    print(f"Data starts at inner offset {data_start:#x} ({data_start})")
    print(f"Total inner size: {len(inner)} bytes")
    print(f"Expected channel count: {(len(inner) - data_start) // RECORD_SIZE}")

    for i in range(num_channels):
        rec_offset = data_start + i * RECORD_SIZE
        if rec_offset + RECORD_SIZE > len(inner):
            break
        probe_channel(inner[rec_offset:rec_offset + RECORD_SIZE], i)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "samples/dm7_empty.dm7f"
    ch   = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    main(path, ch)
