"""fix-spi-slave: SPI mode-0 receiver with wrong shift direction and wrong byte capture."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixSpiSlaveTask(DebugCircuitTask):
    id = "fix-spi-slave"
    sv_filename = "FixSpiSlave.sv"
    config_filename = "fix-spi-slave.json"
    bound = 20
    tier = "3"
    tier_label = "FSM / Multi-register"
    num_properties = 4
    bug_description = "SPI mode-0 slave has 2 bugs: shift register accumulates bits LSB-first instead of MSB-first, and rx_data captures the wrong byte expression"
    hint = "SPI mode 0 receives MSB first. Check the shift direction and the rx_data assignment when bit_cnt reaches 7."
