"""Example hw-cbmc task -- copy this pattern for each task.

Two base classes available (from _base.py):
  - DebugCircuitTask: fix a deliberate logic bug until all assertions PROVE
  - ImplementModuleTask: fill a module stub so all assertions PROVE

Each task needs:
  - A unique `id` (kebab-case)
  - `sv_filename`: name of the .sv (or .smv) file in /workdir/data/
  - `config_filename`: matching JSON in /root_data/eval/configs/
  - `bound`: EBMC bound (default 10; use 1 for combinational, 15-20 for FSM)
  - `tier`: difficulty tier (1-4)

DebugCircuitTask also needs: `bug_description`, `num_properties`
ImplementModuleTask also needs: `num_properties`
"""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class ExampleDebugTask(DebugCircuitTask):
    id = "fix-counter-reset"
    sv_filename = "FixCounterReset.sv"
    config_filename = "fix-counter-reset.json"
    bound = 10
    tier = "2"
    tier_label = "Simple Sequential"
    num_properties = 2
    bug_description = "reset polarity inverted"
