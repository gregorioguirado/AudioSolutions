from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class ChannelColor(Enum):
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"
    PURPLE = "purple"
    CYAN = "cyan"
    WHITE = "white"
    OFF = "off"

class EQBandType(Enum):
    PEAK = "peak"
    LOW_SHELF = "low_shelf"
    HIGH_SHELF = "high_shelf"
    LOW_CUT = "low_cut"
    HIGH_CUT = "high_cut"

@dataclass
class EQBand:
    frequency: float    # Hz
    gain: float         # dB (-20 to +20)
    q: float            # Q factor (0.1 to 16.0)
    band_type: EQBandType
    enabled: bool = True

@dataclass
class Gate:
    threshold: float    # dBFS (-80 to 0)
    attack: float       # ms
    hold: float         # ms
    release: float      # ms
    enabled: bool = False

@dataclass
class Compressor:
    threshold: float    # dBFS (-60 to 0)
    ratio: float        # e.g. 4.0 for 4:1
    attack: float       # ms
    release: float      # ms
    makeup_gain: float  # dB
    enabled: bool = False

@dataclass
class Channel:
    id: int
    name: str
    color: ChannelColor
    input_patch: Optional[int]   # physical input number; None = unpatched
    hpf_frequency: float         # Hz
    hpf_enabled: bool
    eq_bands: list[EQBand] = field(default_factory=list)
    gate: Optional[Gate] = None
    compressor: Optional[Compressor] = None
    mix_bus_assignments: list[int] = field(default_factory=list)
    vca_assignments: list[int] = field(default_factory=list)
    muted: bool = False

@dataclass
class ShowFile:
    source_console: str
    channels: list[Channel] = field(default_factory=list)
    dropped_parameters: list[str] = field(default_factory=list)
