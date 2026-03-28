"""fix-fifo-credit: credit-based FIFO has 3 bugs: credit initialized to 7 instea..."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixFifoCreditTask(DebugCircuitTask):
    id = "fix-fifo-credit"
    sv_filename = "FixFifoCredit.sv"
    config_filename = "fix-fifo-credit.json"
    bound = 10
    tier = "3"
    tier_label = "FSM / Multi-register"
    num_properties = 7
    bug_description = (
        "credit-based FIFO has 3 bugs: credit initialized to 7 instead of 8,"
        " credit returns +2 on read instead of +1, and full signal checks"
        " count==8 instead of credit==0"
    )
    hint = (
        "The design uses credit-based flow control. Think about what invariant"
        " should hold between count and credit, and what signal should drive"
        " 'full'."
    )
