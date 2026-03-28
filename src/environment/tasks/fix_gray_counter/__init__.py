"""fix-gray-counter: 4-bit Gray code counter with wrong reset value, step size, and formula."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixGrayCounterTask(DebugCircuitTask):
    id = "fix-gray-counter"
    sv_filename = "FixGrayCounter.sv"
    config_filename = "fix-gray-counter.json"
    bound = 20
    tier = "2"
    tier_label = "Simple Sequential"
    num_properties = 3
    bug_description = "Gray code counter has 3 bugs: wrong reset output value, binary counter increments by 2 instead of 1, and Gray encoding uses wrong shift amount"
    hint = "Check 3 separate sites: (1) the gray reset value, (2) the bin increment amount, (3) the shift in the Gray encoding formula."
