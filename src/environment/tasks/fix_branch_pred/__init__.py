"""fix-branch-pred: complex interacting-bug task."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixBranchPredTask(DebugCircuitTask):
    id = "fix-branch-pred"
    sv_filename = "FixBranchPred.sv"
    config_filename = "fix-branch-pred.json"
    bound = 10
    tier = "5"
    tier_label = "Pipeline / Microarch"
    num_properties = 7
    bug_description = "3 interacting bugs in data paths"
    hint = "Trace the data flow through the feedback paths. Each bug corrupts a different stage."
