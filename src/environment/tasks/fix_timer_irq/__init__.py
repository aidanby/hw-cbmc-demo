"""fix-timer-irq: complex circuit with interacting wiring bugs."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixTimerIrqTask(DebugCircuitTask):
    id = "fix-timer-irq"
    sv_filename = "FixTimerIrq.sv"
    config_filename = "fix-timer-irq.json"
    bound = 15
    tier = "4"
    tier_label = "Algorithm / Multi-cycle"
    num_properties = 6
    bug_description = "3 interacting wiring bugs in feedback data paths"
    hint = "Trace the data flow through all paths. Bugs interact — fixing one may change symptoms of others."
