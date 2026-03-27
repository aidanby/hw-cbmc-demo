"""fix-counter-reset: 8-bit counter with inverted reset polarity."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixCounterResetTask(DebugCircuitTask):
    id = "fix-counter-reset"
    sv_filename = "FixCounterReset.sv"
    config_filename = "fix-counter-reset.json"
    bound = 10
    tier = "2"
    tier_label = "Simple Sequential"
    num_properties = 2
    bug_description = "reset polarity inverted (!reset vs reset)"
