"""fix-hazard-ctrl: complex circuit with interacting wiring bugs."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixHazardCtrlTask(DebugCircuitTask):
    id = "fix-hazard-ctrl"
    sv_filename = "FixHazardCtrl.sv"
    config_filename = "fix-hazard-ctrl.json"
    bound = 10
    tier = "5"
    tier_label = "Pipeline / Microarch"
    num_properties = 7
    bug_description = "3 interacting wiring bugs in feedback data paths"
    hint = "Trace the data flow through all paths. Bugs interact — fixing one may change symptoms of others."
