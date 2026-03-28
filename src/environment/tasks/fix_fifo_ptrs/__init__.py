"""fix-fifo-ptrs: synchronous FIFO with wrong read index and NBA race on count."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixFifoPtrsTask(DebugCircuitTask):
    id = "fix-fifo-ptrs"
    sv_filename = "FixFifoPtrs.sv"
    config_filename = "fix-fifo-ptrs.json"
    bound = 10
    tier = "3"
    tier_label = "FSM / Multi-register"
    num_properties = 7
    bug_description = (
        "FIFO has 3 bugs: read outputs mem[rd_ptr+1] instead of mem[rd_ptr], "
        "rd_ptr advances by 2 instead of 1 (skipping entries), and "
        "simultaneous write+read causes the last NBA to count to win "
        "(count decrements instead of staying the same)"
    )
    hint = (
        "Bug 1 is in the read data path. Bug 2 is in the read pointer "
        "advancement. Bug 3 requires understanding non-blocking assignment "
        "semantics: when both wr_en and rd_en fire in the same cycle, "
        "which assignment to 'count' takes effect?"
    )
