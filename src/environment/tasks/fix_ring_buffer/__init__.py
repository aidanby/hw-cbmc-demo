"""fix-ring-buffer: ring buffer where count increments on read instead of decrement."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixRingBufferTask(DebugCircuitTask):
    id = "fix-ring-buffer"
    sv_filename = "FixRingBuffer.sv"
    config_filename = "fix-ring-buffer.json"
    bound = 10
    tier = "3"
    tier_label = "FSM / Multi-register"
    num_properties = 4
    bug_description = "ring buffer: count increments on read instead of decrement"
