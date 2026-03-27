"""fix-decoder: 2:4 decoder with missing output[3] case."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixDecoderTask(DebugCircuitTask):
    id = "fix-decoder"
    sv_filename = "FixDecoder.sv"
    config_filename = "fix-decoder.json"
    bound = 1
    tier = "1"
    tier_label = "Combinational"
    num_properties = 3
    bug_description = "2:4 decoder output[3] is wrong (missing case for 2'b11)"
