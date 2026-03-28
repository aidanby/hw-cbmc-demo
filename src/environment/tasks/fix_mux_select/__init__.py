"""fix-mux-select: 4:1 mux with select bits in wrong order."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixMuxSelectTask(DebugCircuitTask):
    id = "fix-mux-select"
    sv_filename = "FixMuxSelect.sv"
    config_filename = "fix-mux-select.json"
    bound = 1
    tier = "1"
    tier_label = "Combinational"
    num_properties = 4
    bug_description = "4:1 mux indexes select bits in wrong order"
