"""fix-cache-ctrl: complex interacting-bug task."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixCacheCtrlTask(DebugCircuitTask):
    id = "fix-cache-ctrl"
    sv_filename = "FixCacheCtrl.sv"
    config_filename = "fix-cache-ctrl.json"
    bound = 8
    tier = "5"
    tier_label = "Pipeline / Microarch"
    num_properties = 7
    bug_description = "3 interacting bugs in data paths"
    hint = "Trace the data flow through the feedback paths. Each bug corrupts a different stage."
