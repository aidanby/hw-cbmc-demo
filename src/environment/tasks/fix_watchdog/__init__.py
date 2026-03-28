"""fix-watchdog: watchdog timer with wrong kick logic and wrong timeout threshold."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixWatchdogTask(DebugCircuitTask):
    id = "fix-watchdog"
    sv_filename = "FixWatchdog.sv"
    config_filename = "fix-watchdog.json"
    bound = 20
    tier = "2"
    tier_label = "Simple Sequential"
    num_properties = 4
    bug_description = "watchdog timer has 2 bugs: kick increments the counter instead of resetting it, and the timeout fires at count 14 instead of 15"
    hint = "Check what 'kick' should do to the counter, and what threshold triggers wdt_reset."
