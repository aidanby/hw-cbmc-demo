"""fix-smv-counter: NuSMV counter that saturates at 15 instead of wrapping to 0."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixSmvCounterTask(DebugCircuitTask):
    id = "fix-smv-counter"
    sv_filename = "fix-smv-counter.smv"
    config_filename = "fix-smv-counter.json"
    bound = 10
    tier = "4"
    tier_label = "NuSMV"
    num_properties = 3
    bug_description = "counter has 2 bugs: wrong initial value (should be 0) and wrong step size (should be +1 not +4)"
    hint = "Check both the init() and next() assignments — there are two independent bugs."
