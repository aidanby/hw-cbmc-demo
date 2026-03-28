"""fix-hamming: Hamming(7,4) encoder with 3 wrong parity equations."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixHammingTask(DebugCircuitTask):
    id = "fix-hamming"
    sv_filename = "FixHamming.sv"
    config_filename = "fix-hamming.json"
    bound = 1
    tier = "1"
    tier_label = "Combinational"
    num_properties = 3
    bug_description = "Hamming(7,4) encoder has 3 bugs: all three parity equations (p1, p2, p4) cover wrong data bit positions"
    hint = "Each parity bit covers positions that share a set bit in the position index: p1 covers positions 1,3,5,7; p2 covers 2,3,6,7; p4 covers 4,5,6,7."
