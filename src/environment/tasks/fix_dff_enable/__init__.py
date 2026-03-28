"""fix-dff-enable: DFF that updates output even when enable=0."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixDffEnableTask(DebugCircuitTask):
    id = "fix-dff-enable"
    sv_filename = "FixDffEnable.sv"
    config_filename = "fix-dff-enable.json"
    bound = 10
    tier = "2"
    tier_label = "Simple Sequential"
    num_properties = 4
    bug_description = "DFF output updates even when enable=0 (enable signal ignored)"
