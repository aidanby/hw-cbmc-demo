"""fix-arb-lock: complex circuit with interacting wiring bugs."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixArbLockTask(DebugCircuitTask):
    id = "fix-arb-lock"
    sv_filename = "FixArbLock.sv"
    config_filename = "fix-arb-lock.json"
    bound = 10
    tier = "5"
    tier_label = "Pipeline / Microarch"
    num_properties = 6
    bug_description = "3 interacting wiring bugs in feedback data paths"
    hint = "Trace the data flow through all paths. Bugs interact — fixing one may change symptoms of others."
