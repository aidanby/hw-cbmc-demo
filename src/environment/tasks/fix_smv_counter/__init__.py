"""fix-smv-counter: NuSMV counter with next(x) := x + 2 instead of x + 1."""
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
    num_properties = 2
    bug_description = "NuSMV counter: next(x) := x + 2 should be x + 1"
