"""Translation verification harness.

This package provides tools to verify the correctness of show file
translations by:

1. Round-tripping a translation (parse source -> write target -> re-parse target)
   and diffing the resulting universal model against the original.
2. Comparing parsed values against pre-recorded "golden" fixture values
   (engine/verification/fixtures/<filename>.yaml) to catch regressions in
   parsers themselves.

The harness is designed to be NON-BLOCKING: hooked into translator.translate()
it logs failures via the standard ``logging`` module under the logger name
``engine.verification`` but never raises.
"""

from .harness import HarnessResult, ParameterCheck, verify_translation
from .round_trip import RoundTripResult, round_trip

__all__ = [
    "HarnessResult",
    "ParameterCheck",
    "RoundTripResult",
    "round_trip",
    "verify_translation",
]
