"""implement-arb3: implement a 3-client round-robin arbiter from stub."""
from typing import final

from environment.tasks._base import ImplementModuleTask


@final
class ImplementArb3Task(ImplementModuleTask):
    id = "implement-arb3"
    sv_filename = "ImplementArb3.sv"
    config_filename = "implement-arb3.json"
    bound = 10
    tier = "3"
    tier_label = "FSM / Multi-register"
    num_properties = 9
