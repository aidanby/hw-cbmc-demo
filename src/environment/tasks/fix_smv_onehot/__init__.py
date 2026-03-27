"""fix-smv-onehot: NuSMV one-hot FSM with wrong next-state for s1."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixSmvOnehotTask(DebugCircuitTask):
    id = "fix-smv-onehot"
    sv_filename = "fix-smv-onehot.smv"
    config_filename = "fix-smv-onehot.json"
    bound = 10
    tier = "4"
    tier_label = "NuSMV"
    num_properties = 3
    bug_description = "one-hot FSM: next(s1) := s0 | s2 should be s0 only"
