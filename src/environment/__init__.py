"""Environment task discovery.

Scans src/environment/tasks/ for Task subclasses.
"""
import importlib
from pathlib import Path
from types import ModuleType


class Task:
    """Base class for environment tasks.

    Required properties:
        id: str               — unique task ID (kebab-case, e.g., "optimize-pipeline")
        steps: list[Step]     — one or more steps the student completes
        tools: list[str]      — tools available to the student (e.g., ["bash", "view_lines_in_file"])
        required_hardware: str — hardware spec (e.g., "cpu-2.8gb", "h100-3g.40gb")
    """
    id: str = ""


class Step:
    """Base class for task steps.

    Required properties:
        instructions: str — what the student sees. Should describe the goal,
                           not the method. Don't mention scoring or grades.
    """
    pass


INCLUDE_TASKS: set[str] = set()
EXCLUDE_TASKS: set[str] = set()


def get_tasks() -> list[type[Task]]:
    import environment.tasks

    tasks: list[type[Task]] = []
    for candidate in Path(environment.tasks.__path__[0]).glob("*"):
        if not candidate.is_dir():
            continue
        if candidate.name.startswith("_"):
            continue
        module = importlib.import_module(f"environment.tasks.{candidate.name}")
        tasks.extend(_get_tasks_from_module(module))
    return tasks


def _get_tasks_from_module(module: ModuleType) -> list[type[Task]]:
    tasks: list[type[Task]] = []
    for member in dir(module):
        cls = getattr(module, member)
        if not isinstance(cls, type) or not issubclass(cls, Task) or cls is Task:
            continue
        id_ = getattr(cls, "id", None)
        if (
            not id_
            or id_ in EXCLUDE_TASKS
            or (INCLUDE_TASKS and id_ not in INCLUDE_TASKS)
        ):
            continue
        tasks.append(cls)
    return tasks
