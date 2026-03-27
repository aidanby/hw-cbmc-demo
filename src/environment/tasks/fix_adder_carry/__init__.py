"""fix-adder-carry: 4-bit adder with buggy carry logic."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixAdderCarryTask(DebugCircuitTask):
    id = "fix-adder-carry"
    sv_filename = "FixAdderCarry.sv"
    config_filename = "fix-adder-carry.json"
    bound = 1
    tier = "1"
    tier_label = "Combinational"
    num_properties = 2
    bug_description = "carry uses & instead of | in sum-of-products carry lookahead"
