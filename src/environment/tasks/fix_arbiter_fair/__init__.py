"""fix-arbiter-fair: 2-client arbiter that always grants client 0."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixArbiterFairTask(DebugCircuitTask):
    id = "fix-arbiter-fair"
    sv_filename = "FixArbiterFair.sv"
    config_filename = "fix-arbiter-fair.json"
    bound = 15
    tier = "3"
    tier_label = "FSM / Multi-register"
    num_properties = 3
    bug_description = "2-client arbiter always grants client 0, ignoring the turn register"
