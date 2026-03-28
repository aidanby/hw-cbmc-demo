"""fix-arbiter-fair: 2-client round-robin arbiter with inverted turn condition."""
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
    num_properties = 6
    bug_description = "round-robin arbiter has 3 bugs: wrong turn value in grant condition, and both turn-update assignments are inverted after granting"
    hint = "Check 3 separate sites: (1) the turn value used in the grant condition, (2) the turn assignment after grant0, (3) the turn assignment after grant1."
