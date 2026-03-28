"""fix-adder-carry: 4-bit carry-lookahead adder with wrong generate term."""
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
    bug_description = "generate terms use | instead of & (over-generates carry, corrupts sum and carry output)"
