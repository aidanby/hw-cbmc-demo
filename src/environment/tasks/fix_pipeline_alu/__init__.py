"""fix-pipeline-alu: 2-stage pipelined ALU with ADD/SUB swapped and wrong WB stage."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixPipelineAluTask(DebugCircuitTask):
    id = "fix-pipeline-alu"
    sv_filename = "FixPipelineAlu.sv"
    config_filename = "fix-pipeline-alu.json"
    bound = 8
    tier = "3"
    tier_label = "FSM / Multi-register"
    num_properties = 5
    bug_description = "2-stage pipelined ALU has 2 bugs: ADD and SUB operations are swapped in the case statement, and the WB stage outputs a_in instead of the computed result"
    hint = "Check the operation case statement and the final output assignment."
