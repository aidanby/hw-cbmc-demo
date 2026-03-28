"""fix-restoring-div: 8-bit restoring division with wrong bit-order and failed restore."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixRestoringDivTask(DebugCircuitTask):
    id = "fix-restoring-div"
    sv_filename = "FixRestoringDiv.sv"
    config_filename = "fix-restoring-div.json"
    bound = 12
    tier = "4"
    tier_label = "Algorithm / Multi-cycle"
    num_properties = 5
    bug_description = (
        "restoring divider has 2 bugs: dividend bits are indexed LSB-first "
        "instead of MSB-first (n_reg[step] vs n_reg[7-step]), and the "
        "restore path keeps the wrong subtracted value instead of restoring "
        "to the shifted partial remainder"
    )
    hint = (
        "Trace the algorithm step by step: which dividend bit should enter "
        "the partial remainder first? And when the subtraction is negative, "
        "what value should be restored?"
    )
