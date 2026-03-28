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
    num_properties = 3
    bug_description = "round-robin arbiter uses turn==1 where it should use turn==0 — always grants client 0 when both request"
