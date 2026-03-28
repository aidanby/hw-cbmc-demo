"""fix-counter-wrap: BCD counter that wraps to wrong reset value."""
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
    num_properties = 4
    bug_description = "BCD counter wraps to 1 instead of 0 (wrong wrap target value)"
