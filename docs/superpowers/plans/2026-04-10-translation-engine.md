# Show File Universal Translator — Plan 1: Translation Engine

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python FastAPI service that accepts a Yamaha CL/QL or DiGiCo SD/Quantum show file, translates it to the opposite format, and returns the translated file plus a translation report.

**Architecture:** Three-layer engine — Parse (read proprietary file into Python objects) → Normalize (convert to console-agnostic universal model) → Write (generate valid output file for target console). Each layer is independently tested. A FastAPI HTTP endpoint wraps the engine.

**Tech Stack:** Python 3.11+, FastAPI, pytest, lxml, zipfile (stdlib), reportlab, uvicorn, Railway (deployment)

**This is Plan 1 of 3.** Plans 2 (Web App & Auth) and 3 (Payments & Entitlements) follow after this engine is deployed and verified.

---

## File Map

```
engine/
├── requirements.txt
├── main.py                        # FastAPI app — POST /translate endpoint
├── translator.py                  # Orchestrates parse → normalize → write
├── report.py                      # Generates PDF translation report
├── models/
│   ├── __init__.py
│   └── universal.py               # Universal show file data model (dataclasses)
├── parsers/
│   ├── __init__.py
│   ├── yamaha_cl.py               # Yamaha CL/QL parser
│   └── digico_sd.py               # DiGiCo SD/Quantum parser
├── writers/
│   ├── __init__.py
│   ├── digico_sd.py               # DiGiCo SD writer (Yamaha → DiGiCo path)
│   └── yamaha_cl.py               # Yamaha CL writer (DiGiCo → Yamaha path)
├── tools/
│   └── examine_file.py            # Format discovery utility (run on real show files)
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── yamaha_cl5_sample.cle  # Synthetic Yamaha test file (ZIP+XML)
    │   └── digico_sd12_sample.show # Synthetic DiGiCo test file (XML)
    ├── test_universal_model.py
    ├── test_yamaha_parser.py
    ├── test_digico_writer.py
    ├── test_digico_parser.py
    ├── test_yamaha_writer.py
    ├── test_translator.py
    └── test_report.py
```

---

## Task 1: Python project setup

**Files:**
- Create: `engine/requirements.txt`
- Create: `engine/models/__init__.py`
- Create: `engine/parsers/__init__.py`
- Create: `engine/writers/__init__.py`
- Create: `engine/tools/__init__.py`
- Create: `engine/tests/__init__.py`
- Create: `engine/tests/fixtures/` (directory)

- [ ] **Step 1: Create the engine directory and requirements file**

```bash
mkdir -p engine/models engine/parsers engine/writers engine/tools engine/tests/fixtures
```

- [ ] **Step 2: Write requirements.txt**

`engine/requirements.txt`:
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
lxml==5.2.1
reportlab==4.2.0
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
```

- [ ] **Step 3: Create empty `__init__.py` files**

```bash
touch engine/models/__init__.py engine/parsers/__init__.py engine/writers/__init__.py engine/tools/__init__.py engine/tests/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
cd engine && pip install -r requirements.txt
```

Expected output: `Successfully installed fastapi-0.111.0 uvicorn-...` (no errors)

- [ ] **Step 5: Verify pytest works**

```bash
cd engine && pytest tests/ -v
```

Expected output: `no tests ran` (not an error — we have no tests yet)

- [ ] **Step 6: Commit**

```bash
git add engine/
git commit -m "feat: scaffold translation engine project structure"
```

---

## Task 2: Universal data model

**Files:**
- Create: `engine/models/universal.py`
- Create: `engine/tests/test_universal_model.py`

- [ ] **Step 1: Write the failing test**

`engine/tests/test_universal_model.py`:
```python
from models.universal import (
    ShowFile, Channel, EQBand, Gate, Compressor, ChannelColor, EQBandType
)

def test_channel_defaults():
    ch = Channel(id=1, name="KICK", color=ChannelColor.RED, input_patch=1,
                 hpf_frequency=80.0, hpf_enabled=True)
    assert ch.eq_bands == []
    assert ch.gate is None
    assert ch.compressor is None
    assert ch.mix_bus_assignments == []
    assert ch.vca_assignments == []
    assert ch.muted is False

def test_showfile_tracks_dropped_parameters():
    sf = ShowFile(source_console="yamaha_cl5")
    sf.dropped_parameters.append("yamaha_premium_rack")
    assert "yamaha_premium_rack" in sf.dropped_parameters

def test_eq_band_types():
    band = EQBand(frequency=1000.0, gain=3.0, q=1.4,
                  band_type=EQBandType.PEAK, enabled=True)
    assert band.frequency == 1000.0
    assert band.band_type == EQBandType.PEAK

def test_compressor_fields():
    comp = Compressor(threshold=-10.0, ratio=4.0, attack=5.0,
                      release=100.0, makeup_gain=2.0, enabled=True)
    assert comp.ratio == 4.0
    assert comp.enabled is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd engine && pytest tests/test_universal_model.py -v
```

Expected: `ImportError: No module named 'models.universal'`

- [ ] **Step 3: Write the universal model**

`engine/models/universal.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd engine && pytest tests/test_universal_model.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add engine/models/universal.py engine/tests/test_universal_model.py
git commit -m "feat: add universal show file data model"
```

---

## Task 3: Format discovery tool

> **CHECKPOINT — run this before Task 4.** The parsers in Tasks 4–8 are written against assumed XML structures. You must obtain real show files from your audio engineering contacts, run this tool on them, and compare the actual XML structure to the test fixtures in Task 4. If they differ, update the fixtures and the parser XPath strings before continuing.

**Files:**
- Create: `engine/tools/examine_file.py`

- [ ] **Step 1: Write the format discovery script**

`engine/tools/examine_file.py`:
```python
#!/usr/bin/env python3
"""
Run this on a real Yamaha .cle or DiGiCo .show file to document its format.
Usage: python tools/examine_file.py path/to/file.cle
"""
import sys
import zipfile
import os


def examine_file(filepath: str) -> None:
    print(f"\n=== Examining: {filepath} ===\n")

    if not os.path.exists(filepath):
        print("ERROR: file not found")
        return

    file_size = os.path.getsize(filepath)
    print(f"File size: {file_size} bytes")

    # Check if ZIP archive
    if zipfile.is_zipfile(filepath):
        print("Format: ZIP archive")
        with zipfile.ZipFile(filepath) as zf:
            print(f"\nContents ({len(zf.namelist())} files):")
            for name in zf.namelist():
                info = zf.getinfo(name)
                print(f"  [{info.file_size:>8} bytes]  {name}")
                with zf.open(name) as f:
                    preview = f.read(400)
                    try:
                        text = preview.decode("utf-8")
                    except UnicodeDecodeError:
                        text = f"[binary: {preview[:20].hex()}...]"
                    print(f"             Preview: {text[:200].strip()}\n")
        return

    # Check if XML / text
    with open(filepath, "rb") as f:
        header = f.read(100)

    if header.lstrip().startswith(b"<?xml") or header.lstrip().startswith(b"<"):
        print("Format: XML text file")
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(2000)
        print("\nFirst 2000 chars:\n")
        print(content)
        return

    # Binary / unknown
    print("Format: Binary / unknown")
    print(f"Header hex: {header.hex()}")
    print(f"Header bytes: {header}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/examine_file.py <path/to/showfile>")
        sys.exit(1)
    examine_file(sys.argv[1])
```

- [ ] **Step 2: Test it on a DiGiCo fixture (we'll create this in Task 4)**

```bash
cd engine && python tools/examine_file.py tests/fixtures/digico_sd12_sample.show
```

Expected: prints "Format: XML text file" and shows the XML structure

- [ ] **Step 3: ⚠️ Run on real files from your network before proceeding**

```bash
# Get a real .cle file from a trusted contact (anonymized/sanitized)
python engine/tools/examine_file.py path/to/real_yamaha.cle

# Get a real .show file from a DiGiCo engineer
python engine/tools/examine_file.py path/to/real_digico.show
```

Compare the output XML structure to the fixtures you'll create in Task 4. If tags differ, update the fixtures and XPath strings in parsers/yamaha_cl.py and parsers/digico_sd.py before running Task 5+.

- [ ] **Step 4: Commit**

```bash
git add engine/tools/examine_file.py
git commit -m "feat: add show file format discovery tool"
```

---

## Task 4: Synthetic test fixtures

> These fixtures represent our best understanding of the file formats. Validate them against real files using `tools/examine_file.py` (Task 3) before relying on them for production.

**Files:**
- Create: `engine/tests/fixtures/digico_sd12_sample.show`
- Create: `engine/tests/fixtures/yamaha_cl5_sample.cle` (ZIP containing XML)
- Create: `engine/tests/conftest.py`

- [ ] **Step 1: Create the DiGiCo sample show file**

`engine/tests/fixtures/digico_sd12_sample.show`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Show ConsoleType="SD12" SoftwareVersion="B179">
  <Channels>
    <Channel Number="1">
      <Name>KICK</Name>
      <Colour>1</Colour>
      <Input>1</Input>
      <HPF>
        <Enabled>1</Enabled>
        <Frequency>80.0</Frequency>
      </HPF>
      <EQ>
        <Band Number="1">
          <Type>PEQ</Type>
          <Frequency>100.0</Frequency>
          <Gain>3.0</Gain>
          <Q>1.4</Q>
          <Enabled>1</Enabled>
        </Band>
        <Band Number="2">
          <Type>PEQ</Type>
          <Frequency>5000.0</Frequency>
          <Gain>-2.0</Gain>
          <Q>2.0</Q>
          <Enabled>1</Enabled>
        </Band>
      </EQ>
      <Gate>
        <Enabled>1</Enabled>
        <Threshold>-40.0</Threshold>
        <Attack>5.0</Attack>
        <Hold>50.0</Hold>
        <Release>200.0</Release>
      </Gate>
      <Compressor>
        <Enabled>1</Enabled>
        <Threshold>-15.0</Threshold>
        <Ratio>4.0</Ratio>
        <Attack>5.0</Attack>
        <Release>100.0</Release>
        <MakeUp>3.0</MakeUp>
      </Compressor>
      <Busses>
        <Bus Number="1" Enabled="1"/>
        <Bus Number="2" Enabled="0"/>
      </Busses>
      <VCAs>
        <VCA Number="1" Enabled="1"/>
      </VCAs>
    </Channel>
    <Channel Number="2">
      <Name>SNARE</Name>
      <Colour>2</Colour>
      <Input>2</Input>
      <HPF>
        <Enabled>1</Enabled>
        <Frequency>120.0</Frequency>
      </HPF>
      <EQ/>
      <Gate>
        <Enabled>0</Enabled>
        <Threshold>-40.0</Threshold>
        <Attack>5.0</Attack>
        <Hold>50.0</Hold>
        <Release>200.0</Release>
      </Gate>
      <Compressor>
        <Enabled>0</Enabled>
        <Threshold>-10.0</Threshold>
        <Ratio>2.0</Ratio>
        <Attack>5.0</Attack>
        <Release>100.0</Release>
        <MakeUp>0.0</MakeUp>
      </Compressor>
      <Busses>
        <Bus Number="1" Enabled="1"/>
      </Busses>
      <VCAs/>
    </Channel>
  </Channels>
</Show>
```

- [ ] **Step 2: Create the Yamaha CL5 sample file (ZIP containing XML)**

Run this Python script once to generate the fixture:

```bash
cd engine && python - << 'EOF'
import zipfile
import io

xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<MixConsole version="1.0" consoleType="CL5">
  <Channels>
    <Channel channelNo="1" channelType="MONO">
      <Name>KICK</Name>
      <Color>RED</Color>
      <Patch>1</Patch>
      <On>true</On>
      <HPF>
        <On>true</On>
        <Freq>80</Freq>
      </HPF>
      <EQ>
        <Band num="1">
          <On>true</On>
          <Type>PEAK</Type>
          <Freq>100</Freq>
          <Gain>3.0</Gain>
          <Q>1.4</Q>
        </Band>
        <Band num="2">
          <On>true</On>
          <Type>PEAK</Type>
          <Freq>5000</Freq>
          <Gain>-2.0</Gain>
          <Q>2.0</Q>
        </Band>
      </EQ>
      <Dynamics1>
        <On>true</On>
        <Threshold>-40</Threshold>
        <Attack>5</Attack>
        <Hold>50</Hold>
        <Decay>200</Decay>
      </Dynamics1>
      <Dynamics2>
        <On>true</On>
        <Threshold>-15</Threshold>
        <Ratio>4.0</Ratio>
        <Attack>5</Attack>
        <Release>100</Release>
        <Gain>3.0</Gain>
      </Dynamics2>
      <Sends>
        <Mix num="1"><On>true</On></Mix>
        <Mix num="2"><On>false</On></Mix>
      </Sends>
      <VCA>
        <Assign num="1">true</Assign>
      </VCA>
    </Channel>
    <Channel channelNo="2" channelType="MONO">
      <Name>SNARE</Name>
      <Color>GREEN</Color>
      <Patch>2</Patch>
      <On>true</On>
      <HPF>
        <On>true</On>
        <Freq>120</Freq>
      </HPF>
      <EQ/>
      <Dynamics1>
        <On>false</On>
        <Threshold>-40</Threshold>
        <Attack>5</Attack>
        <Hold>50</Hold>
        <Decay>200</Decay>
      </Dynamics1>
      <Dynamics2>
        <On>false</On>
        <Threshold>-10</Threshold>
        <Ratio>2.0</Ratio>
        <Attack>5</Attack>
        <Release>100</Release>
        <Gain>0.0</Gain>
      </Dynamics2>
      <Sends>
        <Mix num="1"><On>true</On></Mix>
      </Sends>
      <VCA/>
    </Channel>
  </Channels>
</MixConsole>"""

buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("MixParameter.xml", xml_content)

with open("tests/fixtures/yamaha_cl5_sample.cle", "wb") as f:
    f.write(buf.getvalue())

print("Created tests/fixtures/yamaha_cl5_sample.cle")
EOF
```

- [ ] **Step 3: Create conftest.py with shared fixture paths**

`engine/tests/conftest.py`:
```python
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def yamaha_cl5_fixture() -> Path:
    return FIXTURES_DIR / "yamaha_cl5_sample.cle"

@pytest.fixture
def digico_sd12_fixture() -> Path:
    return FIXTURES_DIR / "digico_sd12_sample.show"
```

- [ ] **Step 4: Verify fixture files exist**

```bash
cd engine && ls tests/fixtures/
```

Expected: `digico_sd12_sample.show  yamaha_cl5_sample.cle`

- [ ] **Step 5: Commit**

```bash
git add engine/tests/
git commit -m "feat: add synthetic show file test fixtures and conftest"
```

---

## Task 5: Yamaha CL/QL parser

**Files:**
- Create: `engine/parsers/yamaha_cl.py`
- Create: `engine/tests/test_yamaha_parser.py`

- [ ] **Step 1: Write the failing tests**

`engine/tests/test_yamaha_parser.py`:
```python
import pytest
from parsers.yamaha_cl import parse_yamaha_cl
from models.universal import ShowFile, ChannelColor, EQBandType

def test_parse_returns_showfile(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    assert isinstance(result, ShowFile)
    assert result.source_console == "yamaha_cl"

def test_parse_channel_count(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    assert len(result.channels) == 2

def test_parse_channel_name(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    assert result.channels[0].name == "KICK"
    assert result.channels[1].name == "SNARE"

def test_parse_channel_color(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    assert result.channels[0].color == ChannelColor.RED
    assert result.channels[1].color == ChannelColor.GREEN

def test_parse_input_patch(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    assert result.channels[0].input_patch == 1
    assert result.channels[1].input_patch == 2

def test_parse_hpf(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert kick.hpf_enabled is True
    assert kick.hpf_frequency == 80.0

def test_parse_eq_bands(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert len(kick.eq_bands) == 2
    assert kick.eq_bands[0].frequency == 100.0
    assert kick.eq_bands[0].gain == 3.0
    assert kick.eq_bands[0].q == 1.4
    assert kick.eq_bands[0].band_type == EQBandType.PEAK
    assert kick.eq_bands[0].enabled is True

def test_parse_gate(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert kick.gate is not None
    assert kick.gate.enabled is True
    assert kick.gate.threshold == -40.0
    assert kick.gate.attack == 5.0
    assert kick.gate.hold == 50.0
    assert kick.gate.release == 200.0

def test_parse_compressor(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert kick.compressor is not None
    assert kick.compressor.enabled is True
    assert kick.compressor.threshold == -15.0
    assert kick.compressor.ratio == 4.0
    assert kick.compressor.makeup_gain == 3.0

def test_parse_mix_bus_assignments(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert 1 in kick.mix_bus_assignments
    assert 2 not in kick.mix_bus_assignments

def test_parse_vca_assignments(yamaha_cl5_fixture):
    result = parse_yamaha_cl(yamaha_cl5_fixture)
    kick = result.channels[0]
    assert 1 in kick.vca_assignments
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd engine && pytest tests/test_yamaha_parser.py -v
```

Expected: `ImportError: No module named 'parsers.yamaha_cl'`

- [ ] **Step 3: Write the Yamaha CL parser**

`engine/parsers/yamaha_cl.py`:
```python
import zipfile
from pathlib import Path
from lxml import etree

from models.universal import (
    ShowFile, Channel, EQBand, Gate, Compressor,
    ChannelColor, EQBandType
)

# Map Yamaha color strings → universal ChannelColor
YAMAHA_COLOR_MAP: dict[str, ChannelColor] = {
    "RED": ChannelColor.RED,
    "GREEN": ChannelColor.GREEN,
    "YELLOW": ChannelColor.YELLOW,
    "BLUE": ChannelColor.BLUE,
    "PURPLE": ChannelColor.PURPLE,
    "CYAN": ChannelColor.CYAN,
    "WHITE": ChannelColor.WHITE,
    "OFF": ChannelColor.OFF,
}

YAMAHA_EQ_TYPE_MAP: dict[str, EQBandType] = {
    "PEAK": EQBandType.PEAK,
    "LPF": EQBandType.HIGH_CUT,
    "HPF": EQBandType.LOW_CUT,
    "LSH": EQBandType.LOW_SHELF,
    "HSH": EQBandType.HIGH_SHELF,
}


def _get_text(element, xpath: str, default: str = "") -> str:
    node = element.find(xpath)
    return node.text.strip() if node is not None and node.text else default


def _get_float(element, xpath: str, default: float = 0.0) -> float:
    text = _get_text(element, xpath)
    try:
        return float(text)
    except (ValueError, TypeError):
        return default


def _get_bool(element, xpath: str, default: bool = False) -> bool:
    text = _get_text(element, xpath).lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    return default


def _parse_channel(ch_elem) -> Channel:
    ch_id = int(ch_elem.get("channelNo", "0"))
    name = _get_text(ch_elem, "Name")
    color_str = _get_text(ch_elem, "Color", "WHITE").upper()
    color = YAMAHA_COLOR_MAP.get(color_str, ChannelColor.WHITE)
    input_patch_str = _get_text(ch_elem, "Patch")
    input_patch = int(input_patch_str) if input_patch_str.isdigit() else None

    hpf_elem = ch_elem.find("HPF")
    hpf_enabled = _get_bool(hpf_elem, "On") if hpf_elem is not None else False
    hpf_frequency = _get_float(hpf_elem, "Freq", 80.0) if hpf_elem is not None else 80.0

    eq_bands: list[EQBand] = []
    eq_elem = ch_elem.find("EQ")
    if eq_elem is not None:
        for band_elem in eq_elem.findall("Band"):
            type_str = _get_text(band_elem, "Type", "PEAK").upper()
            eq_bands.append(EQBand(
                frequency=_get_float(band_elem, "Freq", 1000.0),
                gain=_get_float(band_elem, "Gain", 0.0),
                q=_get_float(band_elem, "Q", 1.0),
                band_type=YAMAHA_EQ_TYPE_MAP.get(type_str, EQBandType.PEAK),
                enabled=_get_bool(band_elem, "On", True),
            ))

    gate: Gate | None = None
    dyn1 = ch_elem.find("Dynamics1")
    if dyn1 is not None:
        gate = Gate(
            threshold=_get_float(dyn1, "Threshold", -40.0),
            attack=_get_float(dyn1, "Attack", 5.0),
            hold=_get_float(dyn1, "Hold", 50.0),
            release=_get_float(dyn1, "Decay", 200.0),
            enabled=_get_bool(dyn1, "On", False),
        )

    compressor: Compressor | None = None
    dyn2 = ch_elem.find("Dynamics2")
    if dyn2 is not None:
        compressor = Compressor(
            threshold=_get_float(dyn2, "Threshold", -10.0),
            ratio=_get_float(dyn2, "Ratio", 1.0),
            attack=_get_float(dyn2, "Attack", 5.0),
            release=_get_float(dyn2, "Release", 100.0),
            makeup_gain=_get_float(dyn2, "Gain", 0.0),
            enabled=_get_bool(dyn2, "On", False),
        )

    mix_buses: list[int] = []
    sends_elem = ch_elem.find("Sends")
    if sends_elem is not None:
        for mix_elem in sends_elem.findall("Mix"):
            if _get_bool(mix_elem, "On", False):
                mix_buses.append(int(mix_elem.get("num", "0")))

    vcas: list[int] = []
    vca_elem = ch_elem.find("VCA")
    if vca_elem is not None:
        for assign_elem in vca_elem.findall("Assign"):
            if (assign_elem.text or "").strip().lower() == "true":
                vcas.append(int(assign_elem.get("num", "0")))

    return Channel(
        id=ch_id,
        name=name,
        color=color,
        input_patch=input_patch,
        hpf_frequency=hpf_frequency,
        hpf_enabled=hpf_enabled,
        eq_bands=eq_bands,
        gate=gate,
        compressor=compressor,
        mix_bus_assignments=mix_buses,
        vca_assignments=vcas,
    )


def parse_yamaha_cl(filepath: Path) -> ShowFile:
    """Parse a Yamaha CL/QL .cle show file into the universal ShowFile model."""
    show = ShowFile(source_console="yamaha_cl")

    with zipfile.ZipFile(filepath) as zf:
        xml_filename = next(
            (n for n in zf.namelist() if n.endswith(".xml")), None
        )
        if xml_filename is None:
            raise ValueError(f"No XML file found inside {filepath}")
        xml_bytes = zf.read(xml_filename)

    root = etree.fromstring(xml_bytes)
    channels_elem = root.find("Channels")
    if channels_elem is None:
        raise ValueError("No <Channels> element found in Yamaha show file")

    for ch_elem in channels_elem.findall("Channel"):
        show.channels.append(_parse_channel(ch_elem))

    return show
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd engine && pytest tests/test_yamaha_parser.py -v
```

Expected: `11 passed`

- [ ] **Step 5: Commit**

```bash
git add engine/parsers/yamaha_cl.py engine/tests/test_yamaha_parser.py
git commit -m "feat: implement Yamaha CL/QL show file parser"
```

---

## Task 6: DiGiCo SD writer (Yamaha → DiGiCo path)

**Files:**
- Create: `engine/writers/digico_sd.py`
- Create: `engine/tests/test_digico_writer.py`

- [ ] **Step 1: Write the failing tests**

`engine/tests/test_digico_writer.py`:
```python
import pytest
from lxml import etree
from parsers.yamaha_cl import parse_yamaha_cl
from writers.digico_sd import write_digico_sd
from models.universal import ChannelColor, EQBandType

def test_write_returns_bytes(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    assert isinstance(result, bytes)

def test_write_produces_valid_xml(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    assert root.tag == "Show"

def test_write_channel_count(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    channels = root.findall(".//Channel")
    assert len(channels) == 2

def test_write_channel_name(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    assert first_channel.findtext("Name") == "KICK"

def test_write_channel_color(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    colour_val = first_channel.findtext("Colour")
    assert colour_val == "1"  # DiGiCo uses integers for colors; 1 = red

def test_write_hpf(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    hpf = first_channel.find("HPF")
    assert hpf.findtext("Enabled") == "1"
    assert float(hpf.findtext("Frequency")) == 80.0

def test_write_eq_bands(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    bands = first_channel.findall(".//Band")
    assert len(bands) == 2
    assert float(bands[0].findtext("Frequency")) == 100.0
    assert float(bands[0].findtext("Gain")) == 3.0

def test_write_gate(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    gate = first_channel.find("Gate")
    assert gate.findtext("Enabled") == "1"
    assert float(gate.findtext("Threshold")) == -40.0

def test_write_compressor(yamaha_cl5_fixture):
    show = parse_yamaha_cl(yamaha_cl5_fixture)
    result = write_digico_sd(show)
    root = etree.fromstring(result)
    first_channel = root.find(".//Channel[@Number='1']")
    comp = first_channel.find("Compressor")
    assert comp.findtext("Enabled") == "1"
    assert float(comp.findtext("Threshold")) == -15.0
    assert float(comp.findtext("MakeUp")) == 3.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd engine && pytest tests/test_digico_writer.py -v
```

Expected: `ImportError: No module named 'writers.digico_sd'`

- [ ] **Step 3: Write the DiGiCo SD writer**

`engine/writers/digico_sd.py`:
```python
from lxml import etree
from models.universal import (
    ShowFile, Channel, EQBand, Gate, Compressor,
    ChannelColor, EQBandType
)

# Universal ChannelColor → DiGiCo integer colour code
DIGICO_COLOR_MAP: dict[ChannelColor, str] = {
    ChannelColor.RED: "1",
    ChannelColor.GREEN: "2",
    ChannelColor.YELLOW: "3",
    ChannelColor.BLUE: "4",
    ChannelColor.PURPLE: "5",
    ChannelColor.CYAN: "6",
    ChannelColor.WHITE: "7",
    ChannelColor.OFF: "0",
}

DIGICO_EQ_TYPE_MAP: dict[EQBandType, str] = {
    EQBandType.PEAK: "PEQ",
    EQBandType.HIGH_CUT: "LPF",
    EQBandType.LOW_CUT: "HPF",
    EQBandType.LOW_SHELF: "LSH",
    EQBandType.HIGH_SHELF: "HSH",
}


def _sub(parent, tag: str, text: str = "") -> etree._Element:
    el = etree.SubElement(parent, tag)
    el.text = text
    return el


def _write_channel(channel: Channel) -> etree._Element:
    ch_elem = etree.Element("Channel", Number=str(channel.id))

    _sub(ch_elem, "Name", channel.name)
    _sub(ch_elem, "Colour", DIGICO_COLOR_MAP.get(channel.color, "7"))
    _sub(ch_elem, "Input", str(channel.input_patch) if channel.input_patch else "0")

    hpf = etree.SubElement(ch_elem, "HPF")
    _sub(hpf, "Enabled", "1" if channel.hpf_enabled else "0")
    _sub(hpf, "Frequency", str(channel.hpf_frequency))

    eq = etree.SubElement(ch_elem, "EQ")
    for i, band in enumerate(channel.eq_bands, start=1):
        b = etree.SubElement(eq, "Band", Number=str(i))
        _sub(b, "Type", DIGICO_EQ_TYPE_MAP.get(band.band_type, "PEQ"))
        _sub(b, "Frequency", str(band.frequency))
        _sub(b, "Gain", str(band.gain))
        _sub(b, "Q", str(band.q))
        _sub(b, "Enabled", "1" if band.enabled else "0")

    gate = etree.SubElement(ch_elem, "Gate")
    if channel.gate:
        _sub(gate, "Enabled", "1" if channel.gate.enabled else "0")
        _sub(gate, "Threshold", str(channel.gate.threshold))
        _sub(gate, "Attack", str(channel.gate.attack))
        _sub(gate, "Hold", str(channel.gate.hold))
        _sub(gate, "Release", str(channel.gate.release))
    else:
        _sub(gate, "Enabled", "0")

    comp = etree.SubElement(ch_elem, "Compressor")
    if channel.compressor:
        _sub(comp, "Enabled", "1" if channel.compressor.enabled else "0")
        _sub(comp, "Threshold", str(channel.compressor.threshold))
        _sub(comp, "Ratio", str(channel.compressor.ratio))
        _sub(comp, "Attack", str(channel.compressor.attack))
        _sub(comp, "Release", str(channel.compressor.release))
        _sub(comp, "MakeUp", str(channel.compressor.makeup_gain))
    else:
        _sub(comp, "Enabled", "0")

    busses = etree.SubElement(ch_elem, "Busses")
    for bus_id in channel.mix_bus_assignments:
        etree.SubElement(busses, "Bus", Number=str(bus_id), Enabled="1")

    vcas = etree.SubElement(ch_elem, "VCAs")
    for vca_id in channel.vca_assignments:
        etree.SubElement(vcas, "VCA", Number=str(vca_id), Enabled="1")

    return ch_elem


def write_digico_sd(show: ShowFile) -> bytes:
    """Write a universal ShowFile to DiGiCo SD/Quantum XML format."""
    root = etree.Element("Show", ConsoleType="SD12", SoftwareVersion="B179")
    channels_elem = etree.SubElement(root, "Channels")

    for channel in show.channels:
        channels_elem.append(_write_channel(channel))

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd engine && pytest tests/test_digico_writer.py -v
```

Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add engine/writers/digico_sd.py engine/tests/test_digico_writer.py
git commit -m "feat: implement DiGiCo SD show file writer"
```

---

## Task 7: DiGiCo SD parser

**Files:**
- Create: `engine/parsers/digico_sd.py`
- Create: `engine/tests/test_digico_parser.py`

- [ ] **Step 1: Write the failing tests**

`engine/tests/test_digico_parser.py`:
```python
import pytest
from parsers.digico_sd import parse_digico_sd
from models.universal import ShowFile, ChannelColor, EQBandType

def test_parse_returns_showfile(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    assert isinstance(result, ShowFile)
    assert result.source_console == "digico_sd"

def test_parse_channel_count(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    assert len(result.channels) == 2

def test_parse_channel_name(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    assert result.channels[0].name == "KICK"
    assert result.channels[1].name == "SNARE"

def test_parse_channel_color(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    assert result.channels[0].color == ChannelColor.RED
    assert result.channels[1].color == ChannelColor.GREEN

def test_parse_input_patch(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    assert result.channels[0].input_patch == 1

def test_parse_hpf(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert kick.hpf_enabled is True
    assert kick.hpf_frequency == 80.0

def test_parse_eq_bands(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert len(kick.eq_bands) == 2
    assert kick.eq_bands[0].frequency == 100.0
    assert kick.eq_bands[0].gain == 3.0
    assert kick.eq_bands[0].band_type == EQBandType.PEAK

def test_parse_gate(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert kick.gate is not None
    assert kick.gate.enabled is True
    assert kick.gate.threshold == -40.0

def test_parse_compressor(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert kick.compressor is not None
    assert kick.compressor.enabled is True
    assert kick.compressor.threshold == -15.0
    assert kick.compressor.makeup_gain == 3.0

def test_parse_mix_bus_assignments(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert 1 in kick.mix_bus_assignments
    assert 2 not in kick.mix_bus_assignments

def test_parse_vca_assignments(digico_sd12_fixture):
    result = parse_digico_sd(digico_sd12_fixture)
    kick = result.channels[0]
    assert 1 in kick.vca_assignments
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd engine && pytest tests/test_digico_parser.py -v
```

Expected: `ImportError: No module named 'parsers.digico_sd'`

- [ ] **Step 3: Write the DiGiCo SD parser**

`engine/parsers/digico_sd.py`:
```python
from pathlib import Path
from lxml import etree

from models.universal import (
    ShowFile, Channel, EQBand, Gate, Compressor,
    ChannelColor, EQBandType
)

DIGICO_COLOR_MAP: dict[str, ChannelColor] = {
    "1": ChannelColor.RED,
    "2": ChannelColor.GREEN,
    "3": ChannelColor.YELLOW,
    "4": ChannelColor.BLUE,
    "5": ChannelColor.PURPLE,
    "6": ChannelColor.CYAN,
    "7": ChannelColor.WHITE,
    "0": ChannelColor.OFF,
}

DIGICO_EQ_TYPE_MAP: dict[str, EQBandType] = {
    "PEQ": EQBandType.PEAK,
    "LPF": EQBandType.HIGH_CUT,
    "HPF": EQBandType.LOW_CUT,
    "LSH": EQBandType.LOW_SHELF,
    "HSH": EQBandType.HIGH_SHELF,
}


def _text(element, tag: str, default: str = "") -> str:
    node = element.find(tag)
    return node.text.strip() if node is not None and node.text else default


def _float(element, tag: str, default: float = 0.0) -> float:
    try:
        return float(_text(element, tag))
    except (ValueError, TypeError):
        return default


def _bool(element, tag: str, default: bool = False) -> bool:
    val = _text(element, tag)
    return val == "1" if val in ("0", "1") else default


def _parse_channel(ch_elem) -> Channel:
    ch_id = int(ch_elem.get("Number", "0"))
    name = _text(ch_elem, "Name")
    colour_val = _text(ch_elem, "Colour", "7")
    color = DIGICO_COLOR_MAP.get(colour_val, ChannelColor.WHITE)

    input_str = _text(ch_elem, "Input", "0")
    input_patch = int(input_str) if input_str.isdigit() and input_str != "0" else None

    hpf_elem = ch_elem.find("HPF")
    hpf_enabled = _bool(hpf_elem, "Enabled") if hpf_elem is not None else False
    hpf_frequency = _float(hpf_elem, "Frequency", 80.0) if hpf_elem is not None else 80.0

    eq_bands: list[EQBand] = []
    eq_elem = ch_elem.find("EQ")
    if eq_elem is not None:
        for band_elem in eq_elem.findall("Band"):
            type_str = _text(band_elem, "Type", "PEQ")
            eq_bands.append(EQBand(
                frequency=_float(band_elem, "Frequency", 1000.0),
                gain=_float(band_elem, "Gain", 0.0),
                q=_float(band_elem, "Q", 1.0),
                band_type=DIGICO_EQ_TYPE_MAP.get(type_str, EQBandType.PEAK),
                enabled=_bool(band_elem, "Enabled", True),
            ))

    gate: Gate | None = None
    gate_elem = ch_elem.find("Gate")
    if gate_elem is not None:
        gate = Gate(
            threshold=_float(gate_elem, "Threshold", -40.0),
            attack=_float(gate_elem, "Attack", 5.0),
            hold=_float(gate_elem, "Hold", 50.0),
            release=_float(gate_elem, "Release", 200.0),
            enabled=_bool(gate_elem, "Enabled", False),
        )

    compressor: Compressor | None = None
    comp_elem = ch_elem.find("Compressor")
    if comp_elem is not None:
        compressor = Compressor(
            threshold=_float(comp_elem, "Threshold", -10.0),
            ratio=_float(comp_elem, "Ratio", 1.0),
            attack=_float(comp_elem, "Attack", 5.0),
            release=_float(comp_elem, "Release", 100.0),
            makeup_gain=_float(comp_elem, "MakeUp", 0.0),
            enabled=_bool(comp_elem, "Enabled", False),
        )

    mix_buses: list[int] = []
    busses_elem = ch_elem.find("Busses")
    if busses_elem is not None:
        for bus_elem in busses_elem.findall("Bus"):
            if bus_elem.get("Enabled") == "1":
                mix_buses.append(int(bus_elem.get("Number", "0")))

    vcas: list[int] = []
    vcas_elem = ch_elem.find("VCAs")
    if vcas_elem is not None:
        for vca_elem in vcas_elem.findall("VCA"):
            if vca_elem.get("Enabled") == "1":
                vcas.append(int(vca_elem.get("Number", "0")))

    return Channel(
        id=ch_id,
        name=name,
        color=color,
        input_patch=input_patch,
        hpf_frequency=hpf_frequency,
        hpf_enabled=hpf_enabled,
        eq_bands=eq_bands,
        gate=gate,
        compressor=compressor,
        mix_bus_assignments=mix_buses,
        vca_assignments=vcas,
    )


def parse_digico_sd(filepath: Path) -> ShowFile:
    """Parse a DiGiCo SD/Quantum .show file into the universal ShowFile model."""
    show = ShowFile(source_console="digico_sd")

    with open(filepath, "rb") as f:
        root = etree.fromstring(f.read())

    channels_elem = root.find("Channels")
    if channels_elem is None:
        raise ValueError("No <Channels> element found in DiGiCo show file")

    for ch_elem in channels_elem.findall("Channel"):
        show.channels.append(_parse_channel(ch_elem))

    return show
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd engine && pytest tests/test_digico_parser.py -v
```

Expected: `11 passed`

- [ ] **Step 5: Commit**

```bash
git add engine/parsers/digico_sd.py engine/tests/test_digico_parser.py
git commit -m "feat: implement DiGiCo SD/Quantum show file parser"
```

---

## Task 8: Yamaha CL writer (DiGiCo → Yamaha path)

**Files:**
- Create: `engine/writers/yamaha_cl.py`
- Create: `engine/tests/test_yamaha_writer.py`

- [ ] **Step 1: Write the failing tests**

`engine/tests/test_yamaha_writer.py`:
```python
import zipfile
import io
import pytest
from lxml import etree
from parsers.digico_sd import parse_digico_sd
from writers.yamaha_cl import write_yamaha_cl

def _get_xml_root(result_bytes: bytes) -> etree._Element:
    buf = io.BytesIO(result_bytes)
    with zipfile.ZipFile(buf) as zf:
        xml_name = next(n for n in zf.namelist() if n.endswith(".xml"))
        return etree.fromstring(zf.read(xml_name))

def test_write_returns_bytes(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    assert isinstance(result, bytes)

def test_write_is_valid_zip(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    buf = io.BytesIO(result)
    assert zipfile.is_zipfile(buf)

def test_write_zip_contains_xml(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    buf = io.BytesIO(result)
    with zipfile.ZipFile(buf) as zf:
        xml_files = [n for n in zf.namelist() if n.endswith(".xml")]
    assert len(xml_files) == 1

def test_write_channel_name(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    root = _get_xml_root(result)
    first = root.find(".//Channel[@channelNo='1']")
    assert first.findtext("Name") == "KICK"

def test_write_channel_color(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    root = _get_xml_root(result)
    first = root.find(".//Channel[@channelNo='1']")
    assert first.findtext("Color") == "RED"

def test_write_hpf(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    root = _get_xml_root(result)
    first = root.find(".//Channel[@channelNo='1']")
    hpf = first.find("HPF")
    assert hpf.findtext("On") == "true"
    assert float(hpf.findtext("Freq")) == 80.0

def test_write_eq_bands(digico_sd12_fixture):
    show = parse_digico_sd(digico_sd12_fixture)
    result = write_yamaha_cl(show)
    root = _get_xml_root(result)
    first = root.find(".//Channel[@channelNo='1']")
    bands = first.findall(".//Band")
    assert len(bands) == 2
    assert float(bands[0].findtext("Freq")) == 100.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd engine && pytest tests/test_yamaha_writer.py -v
```

Expected: `ImportError: No module named 'writers.yamaha_cl'`

- [ ] **Step 3: Write the Yamaha CL writer**

`engine/writers/yamaha_cl.py`:
```python
import io
import zipfile
from lxml import etree
from models.universal import (
    ShowFile, Channel, ChannelColor, EQBandType
)

YAMAHA_COLOR_MAP: dict[ChannelColor, str] = {
    ChannelColor.RED: "RED",
    ChannelColor.GREEN: "GREEN",
    ChannelColor.YELLOW: "YELLOW",
    ChannelColor.BLUE: "BLUE",
    ChannelColor.PURPLE: "PURPLE",
    ChannelColor.CYAN: "CYAN",
    ChannelColor.WHITE: "WHITE",
    ChannelColor.OFF: "OFF",
}

YAMAHA_EQ_TYPE_MAP: dict[EQBandType, str] = {
    EQBandType.PEAK: "PEAK",
    EQBandType.HIGH_CUT: "LPF",
    EQBandType.LOW_CUT: "HPF",
    EQBandType.LOW_SHELF: "LSH",
    EQBandType.HIGH_SHELF: "HSH",
}


def _sub(parent, tag: str, text: str = "") -> etree._Element:
    el = etree.SubElement(parent, tag)
    el.text = text
    return el


def _write_channel(channel: Channel) -> etree._Element:
    ch_elem = etree.Element("Channel",
                            channelNo=str(channel.id),
                            channelType="MONO")

    _sub(ch_elem, "Name", channel.name)
    _sub(ch_elem, "Color", YAMAHA_COLOR_MAP.get(channel.color, "WHITE"))
    _sub(ch_elem, "Patch", str(channel.input_patch) if channel.input_patch else "0")
    _sub(ch_elem, "On", "true")

    hpf = etree.SubElement(ch_elem, "HPF")
    _sub(hpf, "On", "true" if channel.hpf_enabled else "false")
    _sub(hpf, "Freq", str(int(channel.hpf_frequency)))

    eq = etree.SubElement(ch_elem, "EQ")
    for i, band in enumerate(channel.eq_bands, start=1):
        b = etree.SubElement(eq, "Band", num=str(i))
        _sub(b, "On", "true" if band.enabled else "false")
        _sub(b, "Type", YAMAHA_EQ_TYPE_MAP.get(band.band_type, "PEAK"))
        _sub(b, "Freq", str(int(band.frequency)))
        _sub(b, "Gain", str(band.gain))
        _sub(b, "Q", str(band.q))

    dyn1 = etree.SubElement(ch_elem, "Dynamics1")
    if channel.gate:
        _sub(dyn1, "On", "true" if channel.gate.enabled else "false")
        _sub(dyn1, "Threshold", str(channel.gate.threshold))
        _sub(dyn1, "Attack", str(channel.gate.attack))
        _sub(dyn1, "Hold", str(channel.gate.hold))
        _sub(dyn1, "Decay", str(channel.gate.release))
    else:
        _sub(dyn1, "On", "false")

    dyn2 = etree.SubElement(ch_elem, "Dynamics2")
    if channel.compressor:
        _sub(dyn2, "On", "true" if channel.compressor.enabled else "false")
        _sub(dyn2, "Threshold", str(channel.compressor.threshold))
        _sub(dyn2, "Ratio", str(channel.compressor.ratio))
        _sub(dyn2, "Attack", str(channel.compressor.attack))
        _sub(dyn2, "Release", str(channel.compressor.release))
        _sub(dyn2, "Gain", str(channel.compressor.makeup_gain))
    else:
        _sub(dyn2, "On", "false")

    sends = etree.SubElement(ch_elem, "Sends")
    for bus_id in channel.mix_bus_assignments:
        mix = etree.SubElement(sends, "Mix", num=str(bus_id))
        _sub(mix, "On", "true")

    vca_elem = etree.SubElement(ch_elem, "VCA")
    for vca_id in channel.vca_assignments:
        assign = etree.SubElement(vca_elem, "Assign", num=str(vca_id))
        assign.text = "true"

    return ch_elem


def write_yamaha_cl(show: ShowFile) -> bytes:
    """Write a universal ShowFile to Yamaha CL/QL .cle format (ZIP containing XML)."""
    root = etree.Element("MixConsole", version="1.0", consoleType="CL5")
    channels_elem = etree.SubElement(root, "Channels")

    for channel in show.channels:
        channels_elem.append(_write_channel(channel))

    xml_bytes = etree.tostring(root, xml_declaration=True,
                               encoding="UTF-8", pretty_print=True)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("MixParameter.xml", xml_bytes)

    return buf.getvalue()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd engine && pytest tests/test_yamaha_writer.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add engine/writers/yamaha_cl.py engine/tests/test_yamaha_writer.py
git commit -m "feat: implement Yamaha CL/QL show file writer"
```

---

## Task 9: Translator orchestrator

**Files:**
- Create: `engine/translator.py`
- Create: `engine/tests/test_translator.py`

- [ ] **Step 1: Write the failing tests**

`engine/tests/test_translator.py`:
```python
import pytest
from pathlib import Path
from translator import translate, TranslationResult, UnsupportedConsolePair

def test_yamaha_to_digico(yamaha_cl5_fixture):
    result = translate(
        source_file=yamaha_cl5_fixture,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    assert isinstance(result, TranslationResult)
    assert result.output_bytes is not None
    assert len(result.output_bytes) > 0

def test_digico_to_yamaha(digico_sd12_fixture):
    result = translate(
        source_file=digico_sd12_fixture,
        source_console="digico_sd",
        target_console="yamaha_cl",
    )
    assert isinstance(result, TranslationResult)
    assert result.output_bytes is not None

def test_translation_result_has_channel_count(yamaha_cl5_fixture):
    result = translate(
        source_file=yamaha_cl5_fixture,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    assert result.channel_count == 2

def test_translation_result_has_translated_parameters(yamaha_cl5_fixture):
    result = translate(
        source_file=yamaha_cl5_fixture,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    assert len(result.translated_parameters) > 0
    assert "channel_names" in result.translated_parameters

def test_unsupported_pair_raises(yamaha_cl5_fixture):
    with pytest.raises(UnsupportedConsolePair):
        translate(
            source_file=yamaha_cl5_fixture,
            source_console="yamaha_cl",
            target_console="ssl_live",
        )

def test_same_console_raises(yamaha_cl5_fixture):
    with pytest.raises(UnsupportedConsolePair):
        translate(
            source_file=yamaha_cl5_fixture,
            source_console="yamaha_cl",
            target_console="yamaha_cl",
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd engine && pytest tests/test_translator.py -v
```

Expected: `ImportError: No module named 'translator'`

- [ ] **Step 3: Write the translator orchestrator**

`engine/translator.py`:
```python
from dataclasses import dataclass, field
from pathlib import Path

from parsers.yamaha_cl import parse_yamaha_cl
from parsers.digico_sd import parse_digico_sd
from writers.digico_sd import write_digico_sd
from writers.yamaha_cl import write_yamaha_cl
from models.universal import ShowFile


class UnsupportedConsolePair(Exception):
    pass


@dataclass
class TranslationResult:
    output_bytes: bytes
    channel_count: int
    translated_parameters: list[str] = field(default_factory=list)
    approximated_parameters: list[str] = field(default_factory=list)
    dropped_parameters: list[str] = field(default_factory=list)


PARSERS = {
    "yamaha_cl": parse_yamaha_cl,
    "digico_sd": parse_digico_sd,
}

WRITERS = {
    "digico_sd": write_digico_sd,
    "yamaha_cl": write_yamaha_cl,
}


def _collect_translated_parameters(show: ShowFile) -> list[str]:
    """Return a list of parameter types that were successfully parsed."""
    params = ["channel_names", "channel_colors", "input_patch", "hpf"]
    if any(ch.eq_bands for ch in show.channels):
        params.append("eq_bands")
    if any(ch.gate for ch in show.channels):
        params.append("gate")
    if any(ch.compressor for ch in show.channels):
        params.append("compressor")
    if any(ch.mix_bus_assignments for ch in show.channels):
        params.append("mix_bus_routing")
    if any(ch.vca_assignments for ch in show.channels):
        params.append("vca_assignments")
    return params


def translate(
    source_file: Path,
    source_console: str,
    target_console: str,
) -> TranslationResult:
    """
    Parse source_file from source_console format, translate to target_console format.
    Returns a TranslationResult with output bytes and translation metadata.
    """
    if source_console == target_console:
        raise UnsupportedConsolePair(
            f"Source and target console cannot be the same: {source_console}"
        )

    parser = PARSERS.get(source_console)
    writer = WRITERS.get(target_console)

    if parser is None or writer is None:
        supported = ", ".join(PARSERS.keys())
        raise UnsupportedConsolePair(
            f"Unsupported console pair: {source_console} → {target_console}. "
            f"Supported consoles: {supported}"
        )

    show = parser(source_file)
    output_bytes = writer(show)

    return TranslationResult(
        output_bytes=output_bytes,
        channel_count=len(show.channels),
        translated_parameters=_collect_translated_parameters(show),
        approximated_parameters=["eq_band_types", "compressor_ratio_mapping"],
        dropped_parameters=show.dropped_parameters,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd engine && pytest tests/test_translator.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Run the full test suite to make sure nothing broke**

```bash
cd engine && pytest tests/ -v
```

Expected: all tests pass (count will be ~36 by this point)

- [ ] **Step 6: Commit**

```bash
git add engine/translator.py engine/tests/test_translator.py
git commit -m "feat: implement translation orchestrator (parse → normalize → write)"
```

---

## Task 10: Translation report generator

**Files:**
- Create: `engine/report.py`
- Create: `engine/tests/test_report.py`

- [ ] **Step 1: Write the failing tests**

`engine/tests/test_report.py`:
```python
import pytest
from report import generate_report
from translator import TranslationResult

def _make_result() -> TranslationResult:
    return TranslationResult(
        output_bytes=b"fake",
        channel_count=24,
        translated_parameters=["channel_names", "hpf", "eq_bands"],
        approximated_parameters=["eq_band_types"],
        dropped_parameters=["yamaha_premium_rack"],
    )

def test_generate_report_returns_bytes():
    result = _make_result()
    pdf_bytes = generate_report(
        result=result,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0

def test_generate_report_is_pdf():
    result = _make_result()
    pdf_bytes = generate_report(
        result=result,
        source_console="yamaha_cl",
        target_console="digico_sd",
    )
    # PDF files start with %PDF
    assert pdf_bytes[:4] == b"%PDF"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd engine && pytest tests/test_report.py -v
```

Expected: `ImportError: No module named 'report'`

- [ ] **Step 3: Write the report generator**

`engine/report.py`:
```python
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from translator import TranslationResult

CONSOLE_DISPLAY_NAMES = {
    "yamaha_cl": "Yamaha CL/QL",
    "digico_sd": "DiGiCo SD/Quantum",
}


def generate_report(
    result: TranslationResult,
    source_console: str,
    target_console: str,
) -> bytes:
    """Generate a PDF translation report and return it as bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=18)
    story.append(Paragraph("Show File Translation Report", title_style))
    story.append(Spacer(1, 0.5*cm))

    # Summary line
    src_name = CONSOLE_DISPLAY_NAMES.get(source_console, source_console)
    tgt_name = CONSOLE_DISPLAY_NAMES.get(target_console, target_console)
    story.append(Paragraph(
        f"<b>Translation:</b> {src_name} → {tgt_name}",
        styles["Normal"]
    ))
    story.append(Paragraph(
        f"<b>Channels translated:</b> {result.channel_count}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 0.5*cm))

    # WARNING banner
    story.append(Paragraph(
        "⚠️  Always verify this file on the target console before the show. "
        "Load it, check the patch list, and spot-check EQ and dynamics on key channels.",
        ParagraphStyle("warn", parent=styles["Normal"],
                       backColor=colors.lightyellow,
                       borderPadding=6)
    ))
    story.append(Spacer(1, 0.5*cm))

    def section(title: str, items: list[str], color) -> None:
        story.append(Paragraph(title, styles["Heading2"]))
        if not items:
            story.append(Paragraph("None", styles["Normal"]))
        else:
            for item in items:
                story.append(Paragraph(f"• {item.replace('_', ' ').title()}", styles["Normal"]))
        story.append(Spacer(1, 0.3*cm))

    section("✅ Successfully Translated", result.translated_parameters, colors.green)
    section("⚠️  Approximated (verify on desk)", result.approximated_parameters, colors.orange)
    section("❌ Dropped (not available on target)", result.dropped_parameters, colors.red)

    doc.build(story)
    return buf.getvalue()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd engine && pytest tests/test_report.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add engine/report.py engine/tests/test_report.py
git commit -m "feat: implement PDF translation report generator"
```

---

## Task 11: FastAPI HTTP endpoint

**Files:**
- Create: `engine/main.py`

- [ ] **Step 1: Write the FastAPI app**

`engine/main.py`:
```python
import tempfile
import zipfile
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, Response
from translator import translate, UnsupportedConsolePair
from report import generate_report

app = FastAPI(title="Show File Translator Engine", version="1.0.0")

SUPPORTED_CONSOLES = ["yamaha_cl", "digico_sd"]

OUTPUT_FILENAMES = {
    "digico_sd": "translated.show",
    "yamaha_cl": "translated.cle",
}

OUTPUT_CONTENT_TYPES = {
    "digico_sd": "application/xml",
    "yamaha_cl": "application/zip",
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/consoles")
def list_consoles():
    return {"supported_consoles": SUPPORTED_CONSOLES}


@app.post("/translate")
async def translate_file(
    file: UploadFile = File(...),
    source_console: str = Form(...),
    target_console: str = Form(...),
):
    if source_console not in SUPPORTED_CONSOLES:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported source console: {source_console}")
    if target_console not in SUPPORTED_CONSOLES:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported target console: {target_console}")

    # Save uploaded file to a temp path
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        result = translate(
            source_file=tmp_path,
            source_console=source_console,
            target_console=target_console,
        )
        report_pdf = generate_report(
            result=result,
            source_console=source_console,
            target_console=target_console,
        )
    except UnsupportedConsolePair as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Translation failed: {str(e)}")
    finally:
        tmp_path.unlink(missing_ok=True)

    # Return output file + report as a ZIP bundle
    import io
    bundle = io.BytesIO()
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(OUTPUT_FILENAMES[target_console], result.output_bytes)
        zf.writestr("translation_report.pdf", report_pdf)

    return Response(
        content=bundle.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=translation_bundle.zip",
            "X-Channel-Count": str(result.channel_count),
            "X-Translated": ",".join(result.translated_parameters),
            "X-Dropped": ",".join(result.dropped_parameters),
        },
    )
```

- [ ] **Step 2: Smoke test the API locally**

```bash
cd engine && uvicorn main:app --reload --port 8000
```

Expected: `Uvicorn running on http://127.0.0.1:8000`

- [ ] **Step 3: Test the health endpoint (open a second terminal)**

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: Test a real translation via curl**

```bash
curl -X POST http://localhost:8000/translate \
  -F "file=@engine/tests/fixtures/yamaha_cl5_sample.cle" \
  -F "source_console=yamaha_cl" \
  -F "target_console=digico_sd" \
  --output translation_bundle.zip && echo "Success" && ls -lh translation_bundle.zip
```

Expected: `Success` and a non-zero `.zip` file

- [ ] **Step 5: Verify the bundle contents**

```bash
python - << 'EOF'
import zipfile
with zipfile.ZipFile("translation_bundle.zip") as zf:
    print("Bundle contains:", zf.namelist())
EOF
```

Expected: `Bundle contains: ['translated.show', 'translation_report.pdf']`

- [ ] **Step 6: Stop the local server and commit**

Press `Ctrl+C` to stop the server, then:

```bash
git add engine/main.py
git commit -m "feat: add FastAPI HTTP endpoint for show file translation"
```

---

## Task 12: Railway deployment

**Files:**
- Create: `engine/Procfile`
- Create: `engine/railway.toml`

- [ ] **Step 1: Create the Procfile**

`engine/Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 2: Create railway.toml**

`engine/railway.toml`:
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- [ ] **Step 3: Create a Railway account and new project**

1. Go to railway.app and sign up with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect the AudioSolutions repository
4. Set the root directory to `engine/`

- [ ] **Step 4: Verify Railway picks up the Python service**

In the Railway dashboard, the deploy log should show:
```
Installing dependencies from requirements.txt...
Build successful
```

- [ ] **Step 5: Grab the Railway public URL and smoke test**

In Railway dashboard → Settings → Networking → Generate Domain. Copy the URL (e.g., `https://audiosolutions-engine.up.railway.app`).

```bash
curl https://YOUR-RAILWAY-URL.up.railway.app/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 6: Test a real translation against the live engine**

```bash
curl -X POST https://YOUR-RAILWAY-URL.up.railway.app/translate \
  -F "file=@engine/tests/fixtures/yamaha_cl5_sample.cle" \
  -F "source_console=yamaha_cl" \
  -F "target_console=digico_sd" \
  --output translation_bundle.zip && echo "Live engine works"
```

Expected: `Live engine works`

- [ ] **Step 7: Commit deployment config**

```bash
git add engine/Procfile engine/railway.toml
git commit -m "feat: add Railway deployment configuration"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Yamaha CL/QL parser (Tasks 5)
- ✅ DiGiCo SD/Quantum parser (Task 7)
- ✅ DiGiCo SD writer — Yamaha→DiGiCo path (Task 6)
- ✅ Yamaha CL writer — DiGiCo→Yamaha path (Task 8)
- ✅ Universal data model with all required fields (Task 2)
- ✅ Translation report documenting translated/approximated/dropped (Task 10)
- ✅ FastAPI HTTP endpoint (Task 11)
- ✅ Railway deployment (Task 12)
- ✅ Format discovery tool for validating against real files (Task 3)
- ✅ TDD throughout — tests written before every implementation

**Important validation gate:**
Task 3 is a hard checkpoint. The XML structures in the synthetic fixtures are our best approximation of the real formats. Before this plan is considered complete, real show files must be examined using `tools/examine_file.py` and the fixture XML structures validated. If the real formats differ, update the XPath strings in `parsers/yamaha_cl.py` and `parsers/digico_sd.py` accordingly.

**What this plan does NOT cover (Plans 2 and 3):**
- Web app (Next.js upload UI, Vercel deployment)
- User auth (Supabase)
- Payments and entitlements (Paddle)
- File storage (Cloudflare R2)
- Abuse prevention (FingerprintJS, session limits)
