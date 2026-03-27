"""fix-shift-dir: shift register that shifts left instead of right."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixShiftDirTask(DebugCircuitTask):
    id = "fix-shift-dir"
    sv_filename = "FixShiftDir.sv"
    config_filename = "fix-shift-dir.json"
    bound = 10
    tier = "2"
    tier_label = "Simple Sequential"
    num_properties = 2
    bug_description = "shift register shifts left when it should shift right"
