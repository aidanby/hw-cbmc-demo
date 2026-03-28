"""fix-scoreboard-bypass: pipeline with bypass has 3 bugs: bypass condition compares r..."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixScoreboardBypassTask(DebugCircuitTask):
    id = "fix-scoreboard-bypass"
    sv_filename = "FixScoreboardBypass.sv"
    config_filename = "fix-scoreboard-bypass.json"
    bound = 10
    tier = "5"
    tier_label = "Pipeline / Microarch"
    num_properties = 7
    bug_description = (
        "pipeline with bypass has 3 bugs: bypass condition compares"
        " rd_wb==rd_s1 instead of rd_wb==rs_s1 (checks destination match instead"
        " of RAW hazard), bypass mux inputs are swapped (forwards regfile when"
        " bypass active, wb_val when inactive), and increment uses imm_s1+1"
        " instead of src_val+1"
    )
    hint = (
        "A RAW (read-after-write) hazard occurs when the current instruction's"
        " SOURCE register matches the previous instruction's DESTINATION. The"
        " bypass mux should forward the writeback value when a hazard is"
        " detected, and read the register file otherwise."
    )
