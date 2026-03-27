"""fix-counter-wrap: BCD counter that wraps at 15 instead of 9."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixCounterWrapTask(DebugCircuitTask):
    id = "fix-counter-wrap"
    sv_filename = "FixCounterWrap.sv"
    config_filename = "fix-counter-wrap.json"
    bound = 15
    tier = "2"
    tier_label = "Simple Sequential"
    num_properties = 3
    bug_description = "BCD counter wraps at 15 not 9 (off-by-one in wrap condition)"
