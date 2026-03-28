"""fix-priority-enc: 4-to-2 priority encoder with 3 wrong case outputs."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixPriorityEncTask(DebugCircuitTask):
    id = "fix-priority-enc"
    sv_filename = "FixPriorityEnc.sv"
    config_filename = "fix-priority-enc.json"
    bound = 1
    tier = "1"
    tier_label = "Combinational"
    num_properties = 4
    bug_description = "priority encoder has 3 wrong output values: cases 01xx, 001x, and 0001 all return wrong indices"
    hint = "In a 4-to-2 priority encoder, the output index should match the position of the highest set input bit (bit 3 = highest priority = output 3)."
