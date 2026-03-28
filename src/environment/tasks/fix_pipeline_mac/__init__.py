"""fix-pipeline-mac: 3-stage MAC pipeline has 3 bugs: product computes a*a instea..."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixPipelineMacTask(DebugCircuitTask):
    id = "fix-pipeline-mac"
    sv_filename = "FixPipelineMac.sv"
    config_filename = "fix-pipeline-mac.json"
    bound = 10
    tier = "4"
    tier_label = "Algorithm / Multi-cycle"
    num_properties = 6
    bug_description = (
        "3-stage MAC pipeline has 3 bugs: product computes a*a instead of a*b,"
        " accumulator clear checks clr_s1 instead of clr_s2 (one pipeline stage"
        " too early), and accumulator double-adds (acc + prod + prod instead of"
        " acc + prod)"
    )
    hint = (
        "Trace the 3-stage pipeline carefully. Each stage reads OLD register"
        " values due to non-blocking assignments. The clear signal must be"
        " pipelined alongside data."
    )
