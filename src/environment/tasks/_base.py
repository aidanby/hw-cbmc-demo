"""Base classes for hw-cbmc formal hardware verification tasks.

Two task types:
  - DebugCircuitTask: fix a deliberate logic bug until all assertions PROVE
  - ImplementModuleTask: fill a module stub so all assertions PROVE
"""

from abc import abstractmethod
from textwrap import dedent

from environment import Step, Task

_HARDWARE = "cpu-2.8gb"

_ITERATE_SUFFIX = """

IMPORTANT — check your work before considering it done:

    ebmc /workdir/data/{sv_file} --bound {bound}

Interpreting output:
- "PROVED up to bound N" → property passes (good)
- "REFUTED" → property fails, counterexample shown (fix the bug)
- Exit 0 → all properties proved (you're done)
- Exit 10 → at least one property refuted (keep fixing)

Iterate: edit → verify → read counterexample → fix → repeat until exit 0.

CRITICAL — only edit the file for this task:
    /workdir/data/{sv_file}

Your workspace contains ONLY this file. Do not attempt to read or write any
other circuit files.

Reference material is at /workdir/shared/sv_reference.md including SVA syntax
and NuSMV quick reference."""


class HWCBMCTask(Task):
    """Abstract base for all hw-cbmc formal verification tasks."""

    task_type: str = ""
    sv_filename: str = ""
    config_filename: str = ""
    bound: int = 10
    tier: str = ""
    tier_label: str = ""

    @property
    @abstractmethod
    def _core_instructions(self) -> str: ...

    @property
    def task_instructions(self) -> str:
        return self._core_instructions + _ITERATE_SUFFIX.format(
            sv_file=self.sv_filename,
            bound=self.bound,
        )

    @property
    def tools(self):
        return ["bash", "view_lines_in_file", "replace_in_file"]

    @property
    def required_hardware(self):
        return _HARDWARE

    @property
    def steps(self):
        return [
            _HWStep(task_instructions=self.task_instructions),
        ]


class DebugCircuitTask(HWCBMCTask):
    """Fix a deliberate logic bug so all formal assertions PROVE."""

    task_type = "fix_broken"
    bug_description: str = ""
    num_properties: int = 0

    @property
    def _core_instructions(self) -> str:
        return dedent(f"""\
            You have a SystemVerilog file at /workdir/data/{self.sv_filename}
            with {self.num_properties} formal assertion(s). The circuit has a deliberate
            logic bug — one or more of the named assertions are currently REFUTED.

            Your task: find and fix the bug so all assertions PROVE when you run:
                ebmc /workdir/data/{self.sv_filename} --bound {self.bound}

            Hints:
            - Read the assertion names — they describe the invariant being checked
            - Run ebmc first to see the counterexample (it shows the failing trace)
            - Look at the always block and compare the condition to what the assertion expects
            - Only fix the bug; do not remove, rename, or weaken any assertions
            - The module interface (port list) must not be changed""")


class ImplementModuleTask(HWCBMCTask):
    """Implement a module stub so all formal assertions PROVE."""

    task_type = "implement_module"
    num_properties: int = 0

    @property
    def _core_instructions(self) -> str:
        return dedent(f"""\
            You have a SystemVerilog file at /workdir/data/{self.sv_filename}
            with {self.num_properties} formal assertion(s). The module interface and
            assertions are defined, but the body contains // TODO stubs.

            Your task: implement the logic so all assertions PROVE when you run:
                ebmc /workdir/data/{self.sv_filename} --bound {self.bound}

            Hints:
            - Read the assertions carefully — they specify the required behavior
            - Run ebmc first to see what currently fails
            - Implement the logic in the always block / assign statements
            - Do not modify the module signature (port list) or any assertions
            - Reference: /workdir/shared/sv_reference.md for SVA syntax""")


class _HWStep(Step):
    """Single step for hw-cbmc tasks."""

    def __init__(self, *, task_instructions: str):
        self._task_instructions = task_instructions

    @property
    def instructions(self) -> str:
        return self._task_instructions
