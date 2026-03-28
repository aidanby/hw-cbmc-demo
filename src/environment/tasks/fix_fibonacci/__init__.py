"""fix-fibonacci: Fibonacci generator with wrong reset values and wrong recurrence."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixFibonacciTask(DebugCircuitTask):
    id = "fix-fibonacci"
    sv_filename = "FixFibonacci.sv"
    config_filename = "fix-fibonacci.json"
    bound = 15
    tier = "2"
    tier_label = "Simple Sequential"
    num_properties = 4
    bug_description = "Fibonacci generator has 3 bugs: reset sets curr to wrong value, reset sets prev to wrong value, and the recurrence step omits the addition"
    hint = "Check 3 separate sites: the reset value for curr, the reset value for prev, and the combinational expression for the next curr."
