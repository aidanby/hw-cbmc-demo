"""fix-smv-ring3: token-ring mutual exclusion with wrong token cycling."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixSmvRing3Task(DebugCircuitTask):
    id = "fix-smv-ring3"
    sv_filename = "fix-smv-ring3.smv"
    config_filename = "fix-smv-ring3.json"
    bound = 20
    tier = "4"
    tier_label = "NuSMV"
    num_properties = 4
    bug_description = "token-ring FSM has 1 bug: the token transition for process p1 goes to p0 instead of p2, preventing p2 from ever acquiring the token"
    hint = "Check the next(token) case: when token=p1, it should pass to the next process in the ring."
