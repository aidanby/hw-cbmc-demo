"""fix-traffic-light: 4-state FSM with YELLOW stuck in a self-loop."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixTrafficLightTask(DebugCircuitTask):
    id = "fix-traffic-light"
    sv_filename = "FixTrafficLight.sv"
    config_filename = "fix-traffic-light.json"
    bound = 20
    tier = "3"
    tier_label = "FSM / Multi-register"
    num_properties = 3
    bug_description = "4-state FSM: YELLOW state transitions to itself instead of RED (stuck)"
