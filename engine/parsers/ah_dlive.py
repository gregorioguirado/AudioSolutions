"""A&H dLive parser — PENDING CALIBRATION.

dLive show files (.AHsession) are ZIP archives containing XML documents.
Parsing approach will use xml.etree.ElementTree, the same as the DiGiCo
and Yamaha CL XML parsers.

This stub is registered in translator.PARSERS so the console appears in
the supported list and the UI can display it as "coming soon". It raises
NotImplementedError until a real .AHsession sample file is available.

Unblocking steps:
  1. Install dLive Director from allen-heath.com
  2. Create a show with ~10 named channels, HPF on, one gate, one compressor
  3. Save as .AHsession and drop in samples/
  4. Run tools/ah_dlive_probe.py to discover XML field paths
  5. Implement this parser following the pattern in parsers/digico_sd.py
"""
from pathlib import Path
from models.universal import ShowFile


def parse_ah_dlive(filepath: Path) -> ShowFile:
    raise NotImplementedError(
        "A&H dLive parser pending calibration against .AHsession sample file. "
        "See engine/parsers/ah_dlive.py docstring for unblocking steps."
    )
