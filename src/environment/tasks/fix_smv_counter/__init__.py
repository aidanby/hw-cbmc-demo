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
    num_properties = 2
    bug_description = "counter saturates at 15 (TRUE: x) instead of wrapping to 0 (TRUE: 0)"
