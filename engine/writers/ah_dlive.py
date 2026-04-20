"""A&H dLive writer — PENDING CALIBRATION.

Generates a .AHsession ZIP archive from a universal ShowFile.
Approach: build XML tree using ElementTree, zip into the session
folder structure that dLive Director expects.

Blocked on the same .AHsession sample file as the parser — the ZIP
structure and XML schema must be confirmed from a real file before
this can write valid output.
"""
from models.universal import ShowFile


def write_ah_dlive(show: ShowFile) -> bytes:
    raise NotImplementedError(
        "A&H dLive writer pending calibration against .AHsession sample file. "
        "See engine/writers/ah_dlive.py docstring for unblocking steps."
    )
