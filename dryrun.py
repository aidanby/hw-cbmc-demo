#!/usr/bin/env python3
"""Dry-run test: execute scoring + spawn a trial student that attempts a task.

Tiers:
  Tier 1 (always): Test compute_score() with synthetic inputs
  Tier 2 (needs API key): Spawn student agent, scoring runs via Docker if image exists,
                          falls back to local (may fail without domain tools)

Results saved to dryrun-results.json for the LLM reviewer to analyze.

Usage:
    python dryrun.py /path/to/env                    # Full trial (tier 1 + 2)
    python dryrun.py /path/to/env --scoring-only      # Tier 1 only
    python dryrun.py /path/to/env --model gemini/gemini-2.5-flash
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import warnings
warnings.filterwarnings("ignore", module="pydantic")
import concurrent.futures
import tempfile
import time
from pathlib import Path


def find_scoring_script(env_dir: Path) -> Path | None:
    for c in [
        env_dir / "root_data" / "eval" / "scoring.py",
        env_dir / "scoring_data" / "scoring.py",
        env_dir / "root_data" / "scoring_script.py",
    ]:
        if c.exists():
            return c
    for p in (env_dir / "root_data").rglob("scoring.py"):
        return p
    return None


def find_tasks(env_dir: Path) -> list[dict]:
    tasks_dir = env_dir / "src" / "environment" / "tasks"
    if not tasks_dir.exists():
        return []
    tasks = []
    for d in sorted(tasks_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        init = d / "__init__.py"
        if init.exists():
            content = init.read_text()
            id_match = re.search(r'id\s*=\s*["\']([^"\']+)', content)
            task_id = id_match.group(1) if id_match else d.name
            instr_match = re.search(
                r'return\s+dedent\s*\(\s*"""(.*?)"""\s*\)',
                content, re.DOTALL
            )
            if not instr_match:
                instr_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            instructions = instr_match.group(1).strip()[:500] if instr_match else ""
            sv_match = re.search(r'sv_filename\s*=\s*["\']([^"\']+)', content)
            sv_filename = sv_match.group(1) if sv_match else ""
            tasks.append({"id": task_id, "dir": d.name, "instructions": instructions, "sv_filename": sv_filename})
    return tasks


# ============================================================
# Assessment functions (structured analysis for reviewer)
# ============================================================

def assess_path_consistency(env_dir: Path, tasks: list[dict]) -> dict:
    """Check that task instruction paths match what scoring.py reads."""
    scoring_path = find_scoring_script(env_dir)
    if not scoring_path:
        return {"status": "SKIP", "reason": "No scoring script"}

    scoring_code = scoring_path.read_text()

    # Extract paths scoring reads from (open/Path calls with /workdir or /root_data)
    scoring_paths = set(re.findall(
        r'["\'](/workdir/[^"\']+|/root_data/[^"\']+)["\']', scoring_code
    ))

    # Extract output paths from task instructions
    task_output_paths = set()
    for task in tasks:
        instr = task.get("instructions", "")
        # Look for output paths in instructions
        found = re.findall(r'(/workdir/data/output[^\s"\'`,)]+)', instr)
        task_output_paths.update(found)

    # Check for path format mismatches (e.g., task says /workdir/data/output/kernel.py
    # but scoring reads /workdir/data/output/{task_id}/kernel.py)
    mismatches = []
    for tp in task_output_paths:
        # Check if scoring references this path or a pattern that would match
        if not any(tp in sp or sp in tp or
                   # Handle {task_id} pattern substitution
                   re.sub(r'\{[^}]+\}', '[^/]+', sp).replace('/', '\\/') and
                   re.search(re.sub(r'\{[^}]+\}', '[^/]+', sp), tp)
                   for sp in scoring_paths):
            mismatches.append({"task_path": tp, "scoring_paths": list(scoring_paths)})

    return {
        "status": "FAIL" if mismatches else "PASS",
        "task_output_paths": list(task_output_paths),
        "scoring_reads_from": list(scoring_paths),
        "mismatches": mismatches,
    }


def assess_student_comprehension(tool_calls_log: list[str], task_instructions: str) -> dict:
    """Analyze student behavior from tool calls."""
    if not tool_calls_log:
        return {"status": "SKIP", "reason": "No tool calls"}

    first_action = tool_calls_log[0] if tool_calls_log else ""

    # Check for cheat attempts
    cheat_indicators = {
        "tried_root_data": any("/root_data" in c or "/root/" in c for c in tool_calls_log),
        "tried_scoring": any("scoring" in c.lower() for c in tool_calls_log),
        "tried_pip_install": any("pip install" in c for c in tool_calls_log),
        "tried_network": any(kw in c for c in tool_calls_log
                            for kw in ["curl ", "wget ", "git clone"]),
    }

    # Did student read the task data first? (good sign)
    read_first = any(kw in first_action for kw in ["cat ", "ls ", "find ", "head "])

    # Summarize approach from first few commands
    approach_cmds = tool_calls_log[:5]
    approach = "; ".join(c.replace("bash: ", "")[:60] for c in approach_cmds)

    return {
        "status": "WARN" if any(cheat_indicators.values()) else "PASS",
        "understood_task": read_first,
        "first_action": first_action[:150],
        "approach": approach[:300],
        "cheat_attempts": cheat_indicators,
        "suspicious_commands": [c for c in tool_calls_log
                                if any(k in c for k in ["/root_data", "scoring", "chmod", "/root/"])],
    }


def assess_scoring_robustness(env_dir: Path) -> dict:
    """Test scoring with missing/empty/malformed output — should return 0, not crash."""
    scoring_path = find_scoring_script(env_dir)
    if not scoring_path:
        return {"status": "SKIP", "reason": "No scoring script"}

    crashes = []
    results = {}

    test_cases = {
        "missing_output": None,  # output path doesn't exist
        "empty_output": "",      # empty file
        "malformed_output": "not json {{{",  # garbage content
    }

    for case_name, content in test_cases.items():
        with tempfile.TemporaryDirectory(prefix=f"dryrun-robust-{case_name}-") as tmpdir:
            output_file = Path(tmpdir) / "score_output.json"

            if content is not None:
                # Create the "student output" directory with test content
                student_out = Path(tmpdir) / "data" / "output"
                student_out.mkdir(parents=True)
                (student_out / "test_file.py").write_text(content)

            try:
                # Use absolute path for scoring.py and pass a dummy config path
                # Some scoring scripts require config as argv[1] and output as argv[2]
                dummy_config = Path(tmpdir) / "dummy_config.json"
                dummy_config.write_text("{}")
                result = subprocess.run(
                    [sys.executable, str(scoring_path.resolve()), str(dummy_config), str(output_file)],
                    capture_output=True, text=True, timeout=30,
                    env={**os.environ, "PATH": os.environ.get("PATH", "")},
                )
                if output_file.exists():
                    data = json.loads(output_file.read_text())
                    score = data.get("score", -1)
                    # Graceful = score 0 (correct) or at least didn't crash
                    results[case_name] = {"score": score, "handles_gracefully": score == 0.0}
                else:
                    # No output file but didn't crash = graceful
                    # (scoring may rely on external data like bench results)
                    did_not_crash = result.returncode == 0 or "Traceback" not in result.stderr
                    results[case_name] = {"score": None, "handles_gracefully": did_not_crash}
            except subprocess.TimeoutExpired:
                crashes.append(f"{case_name}: timeout")
                results[case_name] = {"score": None, "handles_gracefully": False}
            except Exception as e:
                crashes.append(f"{case_name}: {type(e).__name__}: {e}")
                results[case_name] = {"score": None, "handles_gracefully": False}

    all_graceful = all(r["handles_gracefully"] for r in results.values())
    return {
        "status": "PASS" if all_graceful and not crashes else "WARN",
        "cases": results,
        "crashes": crashes,
    }


def assess_file_format(output_files: list[str], task_instructions: str) -> dict:
    """Check if student produced files in expected format."""
    # Extract expected extensions from instructions
    ext_patterns = re.findall(r'\.(?:py|lean|rs|json|txt|csv|yaml|yml|toml|c|cpp|h)\b',
                              task_instructions)
    expected_exts = list(set(ext_patterns)) if ext_patterns else []

    # Get actual extensions from output
    actual_exts = list(set(
        Path(f).suffix for f in output_files if Path(f).suffix
    ))

    # Check match
    if not expected_exts:
        return {"status": "SKIP", "reason": "No expected extensions detected in instructions"}

    matching = [e for e in expected_exts if e in actual_exts]
    return {
        "status": "PASS" if matching else "WARN",
        "expected_extensions": expected_exts,
        "student_produced": actual_exts,
        "match": bool(matching),
    }


def assess_task_difficulty(env_dir: Path, tasks: list[dict]) -> dict:
    """Test whether tasks are impossible, too easy, or well-calibrated.

    Loads compute_score and per-task configs, then checks:
    - Does a "decent" attempt score > 0? (not impossible)
    - Does a trivial attempt score < 0.5? (not too easy)
    - Do different tasks produce different score ranges? (variation)
    - Is the calibration curve well-distributed? (gradient signal)
    """
    scoring_path = find_scoring_script(env_dir)
    if not scoring_path:
        return {"status": "SKIP", "reason": "No scoring script"}

    # Import compute_score
    import importlib.util
    import inspect
    spec = importlib.util.spec_from_file_location("scoring_diff", scoring_path)
    if not spec or not spec.loader:
        return {"status": "SKIP", "reason": "Cannot import scoring"}

    try:
        module = importlib.util.module_from_spec(spec)
        old_argv = sys.argv
        sys.argv = ["scoring.py", "/tmp/dummy_output.txt"]
        spec.loader.exec_module(module)
        sys.argv = old_argv
    except Exception:
        return {"status": "SKIP", "reason": "Scoring import failed"}

    compute_score = getattr(module, "compute_score", None)
    if not compute_score:
        return {"status": "SKIP", "reason": "No compute_score"}

    sig = inspect.signature(compute_score)
    n_required = len([p for p in sig.parameters.values()
                      if p.default is inspect.Parameter.empty])

    # Read scoring constants from the module
    scoring_code = scoring_path.read_text()
    constants = {}
    for match in re.finditer(r'^([A-Z_]+)\s*=\s*([\d.e+-]+)', scoring_code, re.MULTILINE):
        try:
            constants[match.group(1)] = float(match.group(2))
        except ValueError:
            pass

    # hw-cbmc: compute_score(proved_fraction) — single param in [0, 1]
    # sigmoid(scale * (proved_fraction - center)) calibration
    if n_required == 1:
        # proved_fraction: 0.0 = all refuted, 1.0 = all proved
        test_grid = [
            ("all_refuted", 0.0),
            ("poor", 0.25),
            ("half_proved", 0.5),
            ("decent", 0.6),
            ("good", 0.75),
            ("mostly_proved", 0.9),
            ("all_proved", 1.0),
            ("nan", float("nan")),
        ]

        # Run test grid (1-param)
        calibration = []
        for label, arg1 in test_grid:
            try:
                score = compute_score(arg1)
                if isinstance(score, (int, float)) and math.isfinite(score):
                    calibration.append({"label": label, "args": [arg1], "score": round(score, 4)})
            except Exception:
                calibration.append({"label": label, "args": [arg1], "score": None, "error": True})
    elif n_required == 2:
        test_grid = [
            ("zero", 0.0, 0.0),
            ("poor", 0.2, 0.5),
            ("decent", 0.5, 0.1),
            ("good", 0.7, 0.05),
            ("excellent", 0.9, 0.01),
            ("perfect", 1.0, 0.0),
        ]
        calibration = []
        for label, arg1, arg2 in test_grid:
            try:
                score = compute_score(arg1, arg2)
                if isinstance(score, (int, float)) and math.isfinite(score):
                    calibration.append({"label": label, "args": [arg1, arg2], "score": round(score, 4)})
            except Exception:
                calibration.append({"label": label, "args": [arg1, arg2], "score": None, "error": True})
    else:
        return {"status": "SKIP", "reason": f"Unsupported param count: {n_required}"}

    # Analyze calibration
    scores = [c["score"] for c in calibration if c.get("score") is not None]
    nonzero = [s for s in scores if s > 0]
    high = [s for s in scores if s > 0.8]
    mid = [s for s in scores if 0.1 < s < 0.9]
    distinct = len(set(round(s, 2) for s in scores))

    issues = []
    if not nonzero:
        issues.append("ALL inputs score 0 — scoring may be impossible or gates too tight")
    if len(high) > len(scores) * 0.6:
        issues.append(f"{len(high)}/{len(scores)} inputs score >0.8 — may be too easy")
    if distinct < 3:
        issues.append(f"Only {distinct} distinct score levels — weak gradient signal")
    if len(mid) < 2:
        issues.append(f"Only {len(mid)} scores in 0.1-0.9 — RL training region is narrow")

    # Check task prompt variation
    prompt_set = set()
    for t in tasks:
        # Normalize: strip whitespace, lowercase, remove model names
        instr = t.get("instructions", "").lower().strip()
        # Remove task-specific identifiers to compare structure
        instr = re.sub(r'/workdir/data/[^\s]+', '/PATH', instr)
        instr = re.sub(r'\d+x\d+|\d+\.\d+|\d{3,}', 'N', instr)
        prompt_set.add(instr[:200])

    prompt_variation = len(prompt_set) / len(tasks) if tasks else 0

    if tasks and prompt_variation < 0.3:
        issues.append(
            f"Low prompt variation: {len(prompt_set)} unique prompts across "
            f"{len(tasks)} tasks ({prompt_variation:.0%}) — tasks may converge to one strategy"
        )

    status = "FAIL" if any("impossible" in i.lower() or "ALL inputs" in i for i in issues) else \
             "WARN" if issues else "PASS"

    return {
        "status": status,
        "calibration": calibration,
        "summary": {
            "total_test_points": len(scores),
            "nonzero_scores": len(nonzero),
            "mid_range_scores": len(mid),
            "distinct_levels": distinct,
            "max_score": round(max(scores), 4) if scores else 0,
            "prompt_variation": round(prompt_variation, 2),
            "unique_prompts": len(prompt_set),
            "total_tasks": len(tasks),
        },
        "issues": issues,
    }


# ============================================================
# TIER 1: Scoring function test
# ============================================================

def test_scoring_direct(env_dir: Path) -> dict:
    """Import compute_score and call with synthetic inputs."""
    scoring_path = find_scoring_script(env_dir)
    if not scoring_path:
        return {"status": "SKIP", "reason": "No scoring script found"}

    print(f"  Scoring: {scoring_path.relative_to(env_dir)}")

    import importlib.util
    spec = importlib.util.spec_from_file_location("scoring", scoring_path)
    if not spec or not spec.loader:
        return {"status": "FAIL", "reason": "Cannot import scoring module"}

    try:
        module = importlib.util.module_from_spec(spec)
        old_argv = sys.argv
        sys.argv = ["scoring.py", "/tmp/dummy_output.txt"]
        spec.loader.exec_module(module)
        sys.argv = old_argv
    except Exception as e:
        return {"status": "FAIL", "reason": f"Import crashed: {type(e).__name__}: {e}"}

    compute_score = getattr(module, "compute_score", None)
    if not compute_score:
        return {"status": "FAIL", "reason": "No compute_score() function"}

    import inspect
    sig = inspect.signature(compute_score)
    n_params = len([p for p in sig.parameters.values()
                    if p.default is inspect.Parameter.empty])

    results = {"status": "PASS", "tests": []}

    if n_params == 1:
        cases = [("zero", (0.0,)), ("good", (0.8,)),
                 ("bad", (0.2,)), ("perfect", (1.0,)),
                 ("nan", (float("nan"),))]
    elif n_params == 2:
        cases = [("zero", (0.0, 0.0)), ("good", (1.5, 0.01)),
                 ("bad", (0.5, 0.9)), ("perfect", (2.0, 0.001)),
                 ("nan", (float("nan"), 0.5))]
    elif n_params == 3:
        cases = [("zero", (0.0, 0.0, 0.0)), ("good", (1.0, 0.9, 0.8)),
                 ("bad", (0.0, 0.1, 0.1)), ("perfect", (1.0, 1.0, 1.0))]
    else:
        cases = [("defaults", ())]

    for name, args in cases:
        try:
            score = compute_score(*args)
            valid = isinstance(score, (int, float)) and 0.0 <= score <= 1.0
            results["tests"].append({"name": name, "score": float(score), "valid": valid})
            if not valid:
                results["status"] = "WARN"
        except Exception as e:
            results["tests"].append({"name": name, "error": str(e)})
            results["status"] = "FAIL"

    nonzero = [t for t in results["tests"] if t.get("score", 0) > 0]
    if not nonzero:
        results["status"] = "WARN"
        results["warning"] = "All inputs scored 0.0 — may be too strict or broken"

    return results


# ============================================================
# TIER 2: Local trial with real student agent
# ============================================================

def run_local_trial(env_dir: Path, model: str = "gemini/gemini-2.5-flash", task: dict = None) -> dict:
    """Spawn a student agent that attempts 1 task, writes files, then score.

    Uses LiteLLM for model-agnostic support. Any model with tool use works:
      --model gemini/gemini-2.5-flash          (LLM Provider)
      --model gpt-4o                     (OpenAI)
      --model gemini/gemini-2.0-flash    (Google)
      --model mistral/mistral-large-latest (Mistral)
    """
    tasks = find_tasks(env_dir)
    if not task:
        tasks = find_tasks(env_dir)
        if not tasks:
            return {"status": "SKIP", "reason": "No tasks found"}
        task = tasks[0]

    scoring_path = find_scoring_script(env_dir)
    if not scoring_path:
        return {"status": "SKIP", "reason": "No scoring script"}

    try:
        from litellm import completion
    except ImportError:
        return {"status": "SKIP", "reason": "litellm not installed (pip install litellm)"}

    _api_keys = ["LITELLM_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                  "GEMINI_API_KEY", "AZURE_API_KEY", "AZURE_AI_API_KEY"]
    if not any(os.environ.get(k) for k in _api_keys):
        return {
            "status": "SKIP",
            "reason": "No API key found. Set one of: " + ", ".join(_api_keys),
        }
    print(f"  Task: {task['id']}")
    print(f"  Model: {model}")

    # Create a temp workdir simulating the container layout
    workdir = Path(tempfile.mkdtemp(prefix="dryrun-workdir-"))
    student_data = env_dir / "student_data"
    shared_data = env_dir / "shared_data"

    # Copy ONLY the target circuit file to workdir/data/ (isolation: prevent wrong-file edits)
    data_dir = workdir / "data"
    data_dir.mkdir(parents=True)
    sv_filename = task.get("sv_filename", "")
    if sv_filename and student_data.exists():
        src_file = student_data / sv_filename
        if src_file.exists():
            shutil.copy2(src_file, data_dir / sv_filename)
    elif student_data.exists():
        # Fallback: copy all files if sv_filename unknown
        shutil.copytree(student_data, data_dir, dirs_exist_ok=True)

    # Copy shared data to workdir/shared/
    shared_dir = workdir / "shared"
    if shared_data.exists():
        shutil.copytree(shared_data, shared_dir)
    else:
        shared_dir.mkdir(parents=True)

    # Build student prompt with file context
    context = [f"You are attempting this task:\n\n{task['instructions']}"]
    context.append(f"\nYour working directory is /workdir/data")
    context.append(f"Student data is at /workdir/data/")
    context.append(f"Shared reference is at /workdir/shared/")

    # Include ONLY the target circuit file in context (isolation: one file per task)
    if sv_filename and (data_dir / sv_filename).exists():
        try:
            context.append(f"\n--- data/{sv_filename} ---\n{(data_dir / sv_filename).read_text()}")
        except UnicodeDecodeError:
            pass
    elif not sv_filename and student_data.exists():
        for f in sorted(student_data.rglob("*")):
            if f.is_file() and f.stat().st_size < 3000:
                rel = f.relative_to(student_data)
                try:
                    context.append(f"\n--- data/{rel} ---\n{f.read_text()}")
                except UnicodeDecodeError:
                    pass

    # Include shared data files
    if shared_data.exists():
        for f in sorted(shared_data.rglob("*")):
            if f.is_file() and f.stat().st_size < 3000:
                rel = f.relative_to(shared_data)
                try:
                    context.append(f"\n--- shared/{rel} ---\n{f.read_text()}")
                except UnicodeDecodeError:
                    pass

    prompt = "\n".join(context)
    prompt += f"""

Edit the circuit file at /workdir/data/{sv_filename}. You have access to specialized tools: `read_file` to inspect the circuit, `edit_file` to surgically replace code, and `bash` to run `ebmc` to check properties.
Do NOT use `cat` or `sed` via bash; use the specialized `read_file` and `edit_file` tools.
NOTE: `edit_file` requires EXACT literal string matching for `old_string`. Copy the exact indentation and spacing from the file when replacing.
You can iterate — read the file, identify the bug, fix it, run ebmc to verify, repeat until all properties PROVE.

Do NOT remove, rename, or weaken any assertions. Do NOT try to access /root_data/ or /root/ — those are locked.""".format(sv_filename=sv_filename)

    # Define bash tool (OpenAI-compatible format — LiteLLM translates for all providers)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "bash",
                "description": "Run a bash command. Use to run tests and compile code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The bash command to run"}
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to read"}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "Replace a specific string in a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file"},
                        "old_string": {"type": "string", "description": "Exact text to replace"},
                        "new_string": {"type": "string", "description": "Text to replace it with"}
                    },
                    "required": ["path", "old_string", "new_string"]
                }
            }
        }
    ]

    messages = [{"role": "user", "content": prompt}]
    tool_calls_log = []
    errors = []
    start_time = time.time()

    # Detect docker/podman and check if image exists (needed for container startup below)
    image_name = env_dir.resolve().name.replace("_", "-").replace(" ", "-").lower()
    _docker_cmd = shutil.which("docker") or shutil.which("podman") or "docker"
    docker_available = shutil.which("docker") is not None or shutil.which("podman") is not None
    docker_image_exists = False
    if docker_available:
        try:
            r = subprocess.run(
                [_docker_cmd, "image", "inspect", image_name],
                capture_output=True, timeout=10,
            )
            docker_image_exists = r.returncode == 0
        except Exception:
            pass

    # Start a persistent Docker container for bash commands (if image exists).
    # This gives the student real ebmc + correct paths — no local install needed.
    container_id = None
    if docker_image_exists:
        try:
            r = subprocess.run(
                [
                    _docker_cmd, "run", "-d", "--rm",
                    "-u", "student",
                    "--network", "none",
                    "-v", f"{data_dir}:/workdir/data",
                    "-v", f"{shared_dir}:/workdir/shared:ro",
                    "-w", "/workdir/data",
                    image_name, "sleep", "700",
                ],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode == 0:
                container_id = r.stdout.strip()
                print(f"  Container started ({container_id[:12]}) for bash commands")
            else:
                errors.append(f"Could not start container: {r.stderr[:100]}")
        except Exception as e:
            errors.append(f"Container start error: {e}")

    # Resolve config path once (used for step rewards during edit_file)
    _step_reward_config = None
    if docker_image_exists:
        _config_dir = env_dir / "root_data" / "eval" / "configs"
        if _config_dir.exists():
            _cfgs = sorted(_config_dir.glob("*.json"))
            for _c in _cfgs:
                if task["id"] in _c.stem or _c.stem.replace("-", "_") in task["id"].replace("-", "_"):
                    _step_reward_config = f"/root_data/eval/configs/{_c.name}"
                    break
            if not _step_reward_config and _cfgs:
                _step_reward_config = f"/root_data/eval/configs/{_cfgs[0].name}"

    print(f"  Running student agent...")

    # Multi-turn loop — allow enough turns for complex tasks
    # but cap cost to prevent runaway spending
    MAX_TURNS = 25
    MAX_TIME = 600  # 10 minutes hard wall-clock timeout
    MAX_MESSAGES = 20  # Keep conversation context bounded
    total_tokens_used = 0
    MAX_TOKENS_BUDGET = 200_000  # bounded token budget per trial
    for turn in range(MAX_TURNS):
        # Conversation windowing: keep first message (task prompt) + last N messages
        if len(messages) > MAX_MESSAGES:
            messages = [messages[0]] + messages[-(MAX_MESSAGES - 1):]
        if time.time() - start_time > MAX_TIME:
            errors.append(f"DRYRUN TIMEOUT: Agent exceeded {MAX_TIME}s wall-clock limit. Aborting trial.")
            break
        if total_tokens_used > MAX_TOKENS_BUDGET:
            errors.append(f"Token budget reached ({total_tokens_used:,} tokens)")
            break
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    completion,
                    model=model,
                    max_tokens=4096,
                    tools=tools,
                    messages=messages,
                )
                response = future.result(timeout=60)
        except Exception as e:
            errors.append(f"API error: {e}")
            break

        # Track token usage
        if hasattr(response, "usage") and response.usage:
            total_tokens_used += (response.usage.prompt_tokens or 0) + (response.usage.completion_tokens or 0)

        if not hasattr(response, "choices") or not response.choices:
            errors.append(f"Empty choices in response: {response}")
            break

        choice = response.choices[0]
        assistant_msg = choice.message
        
        # Clean the message dictionary to prevent strict API validation errors on older litellm versions
        msg_dict = assistant_msg.model_dump() if hasattr(assistant_msg, "model_dump") else dict(assistant_msg)
        clean_msg = {k: v for k, v in msg_dict.items() if k in ["role", "content", "tool_calls"] and v is not None}
        
        messages.append(clean_msg)

        # Check for tool calls
        if not hasattr(assistant_msg, "tool_calls") or not assistant_msg.tool_calls:
            break  # Student is done

        # Execute tool calls
        for tc in assistant_msg.tool_calls:
            func = tc.function
            if func.name == "bash":
                try:
                    args = json.loads(func.arguments) if isinstance(func.arguments, str) else func.arguments
                except json.JSONDecodeError:
                    args = {"command": str(func.arguments)}
                cmd = args.get("command", "")
                tool_calls_log.append(f"bash: {cmd[:150]}")
                try:
                    if container_id:
                        # Run inside the live container — real ebmc, correct paths
                        result = subprocess.run(
                            [_docker_cmd, "exec", "-u", "student", "-w", "/workdir/data",
                             container_id, "bash", "-c", cmd],
                            capture_output=True, text=True, timeout=60,
                        )
                    else:
                        # Fallback: run locally with path translation (ebmc won't be available)
                        cmd_local = cmd.replace("/workdir/data/", str(data_dir) + "/")
                        cmd_local = cmd_local.replace("/workdir/shared/", str(shared_dir) + "/")
                        result = subprocess.run(
                            cmd_local, shell=True, capture_output=True, text=True,
                            timeout=30, cwd=str(data_dir), stdin=subprocess.DEVNULL,
                            start_new_session=True
                        )
                    output = (result.stdout + result.stderr)[:2000]
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": output or "(no output)"
                    })
                except subprocess.TimeoutExpired:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": "Command timed out (30s)"
                    })
                    errors.append(f"Timeout: {cmd[:80]}")
            elif func.name == "read_file":
                try:
                    args = json.loads(func.arguments) if isinstance(func.arguments, str) else func.arguments
                    path = args.get("path", "")
                    tool_calls_log.append(f"read_file: {path}")
                    target = workdir / "data" / re.sub(r"^/workdir/data/?", "", path).lstrip("/")
                    if not target.resolve().is_relative_to(workdir / "data"):
                        content = f"Error: Cannot access {path} (outside workspace)"
                    elif not target.exists():
                        content = f"Error: File {path} not found"
                    else:
                        content = target.read_text()[:10000]  # Truncate at 10k chars
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content
                    })
                except Exception as e:
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"Error: {e}"})
            elif func.name == "edit_file":
                try:
                    args = json.loads(func.arguments) if isinstance(func.arguments, str) else func.arguments
                    path = args.get("path", "")
                    old_str = args.get("old_string", "")
                    new_str = args.get("new_string", "")
                    tool_calls_log.append(f"edit_file: {path}")
                    target = workdir / "data" / re.sub(r"^/workdir/data/?", "", path).lstrip("/")
                    if not target.resolve().is_relative_to(workdir / "data"):
                        content = f"Error: Cannot access {path} (outside workspace)"
                    elif not target.exists():
                        content = f"Error: File {path} not found"
                    else:
                        text = target.read_text()
                        if old_str not in text:
                            content = "Error: old_string not found in file exactly as written."
                        else:
                            target.write_text(text.replace(old_str, new_str, 1))
                            content = "File updated successfully."
                            # Step reward: run scoring after each successful edit
                            if container_id and _step_reward_config:
                                try:
                                    sr = subprocess.run(
                                        [_docker_cmd, "exec", "-u", "root", container_id,
                                         "bash", "-c",
                                         f"/root/.venv/bin/python /root_data/eval/scoring.py "
                                         f"{_step_reward_config} /tmp/step_score.json && "
                                         f"cat /tmp/step_score.json"],
                                        capture_output=True, text=True, timeout=30,
                                    )
                                    if sr.returncode == 0 and sr.stdout.strip():
                                        sd = json.loads(sr.stdout.strip())
                                        step_score = sd.get("score", 0)
                                        proved = sd.get("metadata", {}).get("ebmc_proved", "?")
                                        total = sd.get("metadata", {}).get("num_expected_properties", "?")
                                        content += f"\n[Step score: {step_score:.3f} ({proved}/{total} properties proved)]"
                                except Exception:
                                    pass
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content
                    })
                except Exception as e:
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": f"Error: {e}"})
            else:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": f"Unknown tool: {func.name}"
                })

        if choice.finish_reason == "stop":
            break

    elapsed = time.time() - start_time
    print(f"  Student finished in {elapsed:.0f}s ({len(tool_calls_log)} tool calls)")

    # Collect output files
    # Stop the persistent Docker container (it auto-removes due to --rm)
    if container_id:
        try:
            subprocess.run([_docker_cmd, "kill", container_id],
                           capture_output=True, timeout=10)
        except Exception:
            pass
        container_id = None

    output_files = []
    for f in workdir.rglob("*"):
        if f.is_file() and f.relative_to(workdir).parts[0] != "shared":
            output_files.append(str(f.relative_to(workdir)))

    # Try to run scoring — prefer Docker (has all deps), fall back to local
    score = None
    scoring_metadata = {}
    infra_limitations = []
    score_output = workdir / "score_output.json"
    scored_via = "none"

    # (docker_image_exists, image_name, _docker_cmd set earlier before container start)

    if docker_image_exists:
        # Score INSIDE the container — has ebmc, correct paths
        print(f"  Scoring via container ({image_name})...")
        try:
            # Find config matching the task
            config_dir = env_dir / "root_data" / "eval" / "configs"
            first_config = None
            if config_dir.exists():
                configs = sorted(config_dir.glob("*.json"))
                for c in configs:
                    if task["id"] in c.stem or c.stem.replace("-", "_") in task["id"].replace("-", "_"):
                        first_config = f"/root_data/eval/configs/{c.name}"
                        break
                if not first_config and configs:
                    first_config = f"/root_data/eval/configs/{configs[0].name}"

            scoring_result = subprocess.run(
                [
                    _docker_cmd, "run", "--rm", "--user", "root",
                    "-v", f"{data_dir}:/workdir/data", "-v", f"{shared_dir}:/workdir/shared",
                    image_name,
                    "bash", "-c",
                    f"/root/.venv/bin/python /root_data/eval/scoring.py "
                    f"{first_config or '/dev/null'} /tmp/score.json && "
                    f"cat /tmp/score.json"
                ],
                capture_output=True, text=True, timeout=120,
            )
            if scoring_result.returncode == 0 and scoring_result.stdout.strip():
                data = json.loads(scoring_result.stdout.strip())
                score = data.get("score")
                scoring_metadata = data.get("metadata", {})
                scored_via = "container"
                print(f"  Score: {score} (via container)")
            else:
                stderr = scoring_result.stderr[:200] if scoring_result.stderr else ""
                errors.append(f"Docker scoring failed: {stderr}")
        except subprocess.TimeoutExpired:
            errors.append("Docker scoring timed out (120s)")
        except Exception as e:
            errors.append(f"Docker scoring error: {e}")

    elif docker_available:
        print(f"  Docker available but image '{image_name}' not built.")
        print(f"  Run: cd {env_dir} && docker build -f Containerfile -t {image_name} .")
        print(f"  Falling back to local scoring...")

    if scored_via == "none":
        # Fall back to local scoring (may fail if ebmc not installed on host)
        for tool in ["ebmc"]:
            if shutil.which(tool) is None:
                infra_limitations.append(f"{tool} not installed (available in container — build the Docker image)")

        try:
            # Pass dummy config + output path
            dummy_config = workdir / "dummy_config.json"
            dummy_config.write_text("{}")
            scoring_result = subprocess.run(
                [sys.executable, str(scoring_path.resolve()), str(dummy_config), str(score_output)],
                capture_output=True, text=True, timeout=60,
                env={**os.environ, "PATH": os.environ.get("PATH", "")},
            )
            if score_output.exists():
                data = json.loads(score_output.read_text())
                score = data.get("score")
                scoring_metadata = data.get("metadata", {})
                scored_via = "local"
                print(f"  Score: {score} (local)")
                if score == 0.0 and infra_limitations:
                    print(f"  Note: score=0 likely due to missing local tools, not a bug")
                    print(f"  Build the Docker image for accurate scoring:")
                    print(f"    cd {env_dir} && docker build -f Containerfile -t {image_name} .")
            else:
                stderr = scoring_result.stderr[:200] if scoring_result.stderr else ""
                if any(kw in stderr for kw in ["not found", "No such file", "ModuleNotFoundError"]):
                    infra_limitations.append(f"Scoring dependency missing: {stderr[:100]}")
                else:
                    errors.append(f"Scoring stderr: {stderr}")
        except subprocess.TimeoutExpired:
            errors.append("Scoring timed out (60s)")
        except Exception as e:
            errors.append(f"Scoring error: {e}")

    # Smart transcript truncation for reviewer
    truncated_calls = []
    if tool_calls_log:
        # First 3 + last 3 + any suspicious ones
        suspicious = [c for c in tool_calls_log if any(
            p in c for p in ["/root_data", "scoring", "chmod", "/root/"]
        )]
        first_last = tool_calls_log[:3] + (tool_calls_log[-3:] if len(tool_calls_log) > 6 else tool_calls_log[3:])
        truncated_calls = list(dict.fromkeys(first_last + suspicious))  # dedupe, preserve order

    # Extract student strategy from first assistant message
    strategy = ""
    for msg in messages:
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", "")
        if role == "assistant":
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            if isinstance(content, str) and content:
                strategy = content[:300]
                break

    # === Structured assessments ===
    print(f"  Running assessments...")
    assessment = {
        "path_consistency": assess_path_consistency(env_dir, tasks),
        "student_comprehension": assess_student_comprehension(tool_calls_log, task["instructions"]),
        "file_format": assess_file_format(output_files, task["instructions"]),
        "scoring_robustness": assess_scoring_robustness(env_dir),
    }

    # Print assessment summary
    for name, a in assessment.items():
        print(f"    {name}: {a['status']}")

    result = {
        "status": "PASS" if score is not None else "WARN",
        "task": task["id"],
        "score": score,
        "scoring_metadata": scoring_metadata,
        "student_strategy": strategy,
        "tool_calls_summary": truncated_calls,
        "tool_calls_total": len(tool_calls_log),
        "output_files": output_files[:20],
        "errors": errors,
        "infra_limitations": infra_limitations,
        "time_seconds": round(elapsed, 1),
        "assessment": assessment,
    }

    # Cleanup
    shutil.rmtree(workdir, ignore_errors=True)
    return result


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Dry-run test for RL environments")
    parser.add_argument("env_dir", help="Path to the environment")
    parser.add_argument("--scoring-only", action="store_true")
    parser.add_argument("--student-only", action="store_true")
    parser.add_argument("--model", default="gemini/gemini-2.5-flash")
    parser.add_argument("--output", "-o", help="Save results JSON to this path")
    parser.add_argument("--all-tasks", action="store_true", help="Run dryrun for all tasks")
    args = parser.parse_args()

    env_dir = Path(args.env_dir)
    if not env_dir.exists():
        print(f"Error: {env_dir} does not exist")
        sys.exit(1)

    print(f"Dry-run testing: {env_dir.name}")
    print()

    all_results = {"tier": "unknown", "results": []}
    all_pass = True

    # Tier 1: Scoring test + assessments that don't need a student
    if not args.student_only:
        print("[Tier 1] Testing compute_score() with synthetic inputs...")
        result1 = test_scoring_direct(env_dir)
        print(f"  Result: {result1['status']}")
        if result1.get("tests"):
            for t in result1["tests"]:
                if "error" in t:
                    print(f"    {t['name']}: CRASH — {t['error']}")
                else:
                    print(f"    {t['name']}: score={t['score']:.4f} {'OK' if t.get('valid') else 'BAD'}")
        if result1.get("warning"):
            print(f"  Warning: {result1['warning']}")
        if result1["status"] == "FAIL":
            all_pass = False
        all_results["tier1_scoring"] = result1
        print()

        # Assessments that work without a student agent
        tasks = find_tasks(env_dir)
        print("[Tier 1b] Path consistency check...")
        path_result = assess_path_consistency(env_dir, tasks)
        print(f"  Result: {path_result['status']}")
        if path_result.get("mismatches"):
            for m in path_result["mismatches"]:
                print(f"    Mismatch: {m['task_path']}")
        all_results["path_consistency"] = path_result

        print("[Tier 1c] Scoring robustness check...")
        robust_result = assess_scoring_robustness(env_dir)
        print(f"  Result: {robust_result['status']}")
        for case, r in robust_result.get("cases", {}).items():
            status = "OK" if r["handles_gracefully"] else "PROBLEM"
            print(f"    {case}: {status} (score={r.get('score')})")
        if robust_result.get("crashes"):
            for c in robust_result["crashes"]:
                print(f"    CRASH: {c}")
        all_results["scoring_robustness"] = robust_result
        print()

        print("[Tier 1d] Task difficulty & calibration check...")
        diff_result = assess_task_difficulty(env_dir, tasks)
        print(f"  Result: {diff_result['status']}")
        summary = diff_result.get("summary", {})
        print(f"    Scores: {summary.get('nonzero_scores', 0)} nonzero, "
              f"{summary.get('mid_range_scores', 0)} mid-range, "
              f"{summary.get('distinct_levels', 0)} distinct levels, "
              f"max={summary.get('max_score', 0)}")
        print(f"    Prompts: {summary.get('unique_prompts', 0)} unique / "
              f"{summary.get('total_tasks', 0)} tasks "
              f"({summary.get('prompt_variation', 0):.0%} variation)")
        if diff_result.get("calibration"):
            cal_str = " | ".join(
                f"{c['label']}={c['score']}" for c in diff_result["calibration"]
                if c.get("score") is not None
            )
            print(f"    Curve: {cal_str}")
        for issue in diff_result.get("issues", []):
            print(f"    ISSUE: {issue}")
        all_results["task_difficulty"] = diff_result
        print()

        # Tier 2: Local trial student
    if not args.scoring_only:
        tasks = find_tasks(env_dir)
        tasks_to_run = tasks if args.all_tasks else (tasks[:1] if tasks else [])
        print(f"[Tier 2] Local trial: spawning student agent for {len(tasks_to_run)} task(s)...")
        all_results["tier"] = "local_trial"
        
        for idx, t in enumerate(tasks_to_run):
            print(f"--- Task {idx+1}/{len(tasks_to_run)}: {t['id']} ---")
            result2 = run_local_trial(env_dir, args.model, t)
            print(f"  Result: {result2['status']}")
            if result2.get("score") is not None:
                print(f"  Score: {result2['score']}")
            if result2.get("errors"):
                for e in result2["errors"]:
                    print(f"  Error: {e}")
            if result2.get("tool_calls_total"):
                print(f"  Tool calls: {result2['tool_calls_total']}")
            if result2.get("output_files"):
                print(f"  Output files: {len(result2['output_files'])}")
            if result2["status"] == "FAIL":
                all_pass = False
            all_results["results"].append(result2)
            print()
            
        print("\n### Performance Summary")
        print("| Task | Status | Score | Time (s) | Tool Calls |")
        print("|---|---|---|---|---|")
        for res in all_results["results"]:
            score = res.get('score')
            if score is None:
                score_str = 'N/A'
            elif isinstance(score, float):
                score_str = f"{score:.4f}"
            else:
                score_str = str(score)
            task_name = res.get('task', 'unknown')
            print(f"| {task_name} | {res['status']} | {score_str} | {res.get('time_seconds', 'N/A')} | {res.get('tool_calls_total', 'N/A')} |")

    # Save results
    output_path = args.output or str(env_dir / "dryrun-results.json")
    Path(output_path).write_text(json.dumps(all_results, indent=2, default=str))
    print(f"Results saved to {output_path}")

    print()
    print("=" * 40)
    print(f"DRY RUN: {'PASS' if all_pass else 'ISSUES FOUND'}")
    print("=" * 40)


if __name__ == "__main__":
    main()
