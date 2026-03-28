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
    bug_description = "one-hot FSM has 2 bugs: next(s1) uses s0|s2 instead of s0 only, and next(s2) uses s0 instead of s1"
    hint = "Two next-state assignments are wrong. For each state, trace which predecessor should activate it in the correct s0→s1→s2→s0 cycle."
