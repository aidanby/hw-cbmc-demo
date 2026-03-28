"""fix-crc8: CRC-8/SMBUS serial register with wrong reset value and wrong polynomial."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixCRC8Task(DebugCircuitTask):
    id = "fix-crc8"
    sv_filename = "FixCRC8.sv"
    config_filename = "fix-crc8.json"
    bound = 15
    tier = "2"
    tier_label = "Simple Sequential"
    num_properties = 3
    bug_description = "CRC-8 register has 2 bugs: reset initializes to 0xFF instead of 0x00, and the feedback polynomial is 0x83 instead of the correct CRC-8/SMBUS polynomial 0x07"
    hint = "Check 2 separate sites: (1) the reset value of crc, (2) the XOR polynomial constant used in the feedback branch."
