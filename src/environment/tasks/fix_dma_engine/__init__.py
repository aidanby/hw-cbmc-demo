"""fix-dma-engine: complex interacting-bug task."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixDmaEngineTask(DebugCircuitTask):
    id = "fix-dma-engine"
    sv_filename = "FixDmaEngine.sv"
    config_filename = "fix-dma-engine.json"
    bound = 12
    tier = "5"
    tier_label = "Pipeline / Microarch"
    num_properties = 7
    bug_description = "3 interacting bugs in data paths"
    hint = "Trace the data flow through the feedback paths. Each bug corrupts a different stage."
