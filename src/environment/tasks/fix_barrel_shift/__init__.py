"""fix-barrel-shift: 8-bit logical right barrel shifter with 4 bugs across shift cases."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixBarrelShiftTask(DebugCircuitTask):
    id = "fix-barrel-shift"
    sv_filename = "FixBarrelShift.sv"
    config_filename = "fix-barrel-shift.json"
    bound = 1
    tier = "1"
    tier_label = "Combinational"
    num_properties = 4
    bug_description = "barrel shifter has 4 bugs: sel=0 outputs 0 instead of input, sel=1 uses arithmetic (sign-extending) shift instead of logical (zero-filling), and cases sel=4 and sel=7 are swapped"
    hint = "Check 4 cases: (1) sel=0 should pass input unchanged, (2) sel=1 should zero-fill not sign-extend, (3) sel=4 and sel=7 outputs are exchanged."
