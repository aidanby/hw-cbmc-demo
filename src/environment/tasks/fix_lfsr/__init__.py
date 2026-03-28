"""fix-lfsr: 4-bit LFSR with wrong seed, reset value, and feedback taps."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixLFSRTask(DebugCircuitTask):
    id = "fix-lfsr"
    sv_filename = "FixLFSR.sv"
    config_filename = "fix-lfsr.json"
    bound = 20
    tier = "2"
    tier_label = "Simple Sequential"
    num_properties = 3
    bug_description = "4-bit LFSR has 3 bugs: zero initial seed (locks up without reset), wrong reset value, and wrong feedback tap (q[1] instead of q[2])"
    hint = "Three distinct bugs: (1) initial seed value, (2) reset target value, (3) which bit is XORed with q[3] for feedback."
