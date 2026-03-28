"""fix-uart-rx: UART receiver has 3 bugs: mid-bit sampling at tick 15 instea..."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixUartRxTask(DebugCircuitTask):
    id = "fix-uart-rx"
    sv_filename = "FixUartRx.sv"
    config_filename = "fix-uart-rx.json"
    bound = 15
    tier = "4"
    tier_label = "Protocol FSM"
    num_properties = 6
    bug_description = (
        "UART receiver has 3 bugs: mid-bit sampling at tick 15 instead of 7"
        " (16x oversampling means mid-bit is at tick 7-8), shift register loads"
        " MSB-first instead of LSB-first, and stop bit check is inverted"
    )
    hint = (
        "UART 8N1 uses 16x oversampling. Mid-bit sampling should happen at the"
        " CENTER of the bit period (tick 7, not the end at tick 15). Data is"
        " transmitted LSB-first. Stop bit is HIGH (idle line state)."
    )
