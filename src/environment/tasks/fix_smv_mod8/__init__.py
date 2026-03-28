"""fix-smv-mod8: modulo-8 counter with wrong step and wrong wrap."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixSmvMod8Task(DebugCircuitTask):
    id = "fix-smv-mod8"
    sv_filename = "fix-smv-mod8.smv"
    config_filename = "fix-smv-mod8.json"
    bound = 20
    tier = "4"
    tier_label = "NuSMV"
    num_properties = 4
    bug_description = "counter has 2 bugs: wrap case goes to 1 instead of 0, and the default step is +2 instead of +1"
    hint = "Check 2 sites: (1) the wrap value when x=7, (2) the step size for all other values."
