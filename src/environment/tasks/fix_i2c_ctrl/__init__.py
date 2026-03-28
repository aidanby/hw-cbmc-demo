"""fix-i2c-ctrl: I2C master has 3 bugs: SDA output-enable polarity wrong for ..."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixI2cCtrlTask(DebugCircuitTask):
    id = "fix-i2c-ctrl"
    sv_filename = "FixI2cCtrl.sv"
    config_filename = "fix-i2c-ctrl.json"
    bound = 12
    tier = "4"
    tier_label = "Protocol FSM"
    num_properties = 6
    bug_description = (
        "I2C master has 3 bugs: SDA output-enable polarity wrong for data bits"
        " (open-drain: oe=1 drives LOW, oe=0 releases to HIGH), bit index counts"
        " up instead of down (I2C sends MSB first), and ACK detection inverted"
        " (ACK = slave pulls SDA LOW)"
    )
    hint = (
        "Open-drain: output-enable=1 means DRIVE LINE LOW, =0 means RELEASE"
        " (external pull-up brings HIGH). To transmit a '0', drive SDA low"
        " (oe=1). To transmit a '1', release SDA (oe=0). I2C sends MSB first"
        " using a decrementing bit counter."
    )
