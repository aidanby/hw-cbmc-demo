#!/usr/bin/env python3
"""Finalize README.md with baseline performance table and env summary.

Auto-discovers multi-run result files ({model}_run{N}.json) and computes
mean ± standard deviation across runs. Supports multiple models.

Run after dry-runs complete. Idempotent. Replaces existing sections if present.

Usage:
    python3 finalize_readme.py <env-dir> [--model MODEL_NAME]
"""

import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _std(values):
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (len(values) - 1))


def _score_to_color(score):
    """Map score [0,1] to red-yellow-green hex color."""
    if score is None:
        return '#cccccc'
    s = max(0.0, min(1.0, score))
    if s <= 0.5:
        r, g = 255, int(255 * (s / 0.5))
    else:
        r, g = int(255 * ((1 - s) / 0.5)), 255
    return f'#{r:02x}{g:02x}50'


def _row_relative_color(value, all_values, higher_is_better=True):
    """Color relative to other values in the same row.

    Best=green, middle=yellow, worst=red. Works with any number of models.
    """
    valid = [v for v in all_values if v is not None]
    if value is None or len(valid) < 1:
        return '#e8e8e8'
    if len(valid) == 1:
        return '#b0ffb0'
    lo, hi = min(valid), max(valid)
    if hi == lo:
        return '#ffffb0'
    t = (value - lo) / (hi - lo)  # 0=worst, 1=best
    if not higher_is_better:
        t = 1.0 - t
    # Red → yellow → green (3-stop gradient)
    if t <= 0.5:
        # Red to yellow: R stays 255, G rises 0→255
        r, g = 255, int(255 * (t / 0.5))
    else:
        # Yellow to green: R drops 255→0, G stays 255
        r, g = int(255 * ((1.0 - t) / 0.5)), 255
    return f'#{r:02x}{g:02x}50'


def generate_heatmap_svg(model_stats: dict, model_names: list, all_tasks: list,
                         runs_per_model: dict = None, task_difficulty: dict = None,
                         model_pass_rates: dict = None, model_averages: dict = None) -> str:
    """Generate a unified SVG heatmap with score, time, and tools per model.

    Colors are RELATIVE PER ROW: within each task, best=green, worst=red.
    Score cells with mean < 0.10 are always red (absolute floor) regardless of row rank.
    task_difficulty: optional {task_name: "easy"|"medium"|"hard"} — adds colored dots.
    model_pass_rates: optional {model: (n_solved, n_total)} — shown in column header.
    model_averages: optional {model: mean_score} — shown in pinned AVERAGE row at top.
    """
    n_models = len(model_names)
    # Each model gets 3 sub-columns: score, time, tools
    sub_w = 64
    model_group_w = sub_w * 3
    dot_offset = 12 if task_difficulty else 0
    task_col_w = max(130, max((len(t) * 6.5 + 10 + dot_offset) for t in all_tasks) if all_tasks else 130)
    header_h = 70  # model name + N=runs + pass rate + avg + sub-column labels
    avg_row_h = 34  # (kept for height calculation compat)
    row_h = 32  # taller to fit mean + ±std
    n_data_rows = len(all_tasks)
    w = int(task_col_w + model_group_w * n_models + 10)
    h = int(header_h + row_h * len(all_tasks) + 5)

    L = []
    L.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="ui-monospace,monospace" font-size="10">')
    L.append('<style>'
             'text{fill:#1f2328}'
             '@media(prefers-color-scheme:dark){'
             f'.bg{{fill:#161b22}}'
             'text{fill:#e6edf3}'
             '.cell{fill:#1f2328 !important}'
             '.dim{fill:#8b949e !important}'
             '.sep{stroke:#30363d}'
             '}'
             '</style>')
    L.append(f'<rect class="bg" width="{w}" height="{h}" fill="#fff" rx="5"/>')

    # Header row 1: model names + N=runs + pass rate
    x = task_col_w
    for model in model_names:
        label = model.split("/")[-1]
        for prefix in ["claude-", "anthropic-", "openai-"]:
            if label.startswith(prefix):
                label = label[len(prefix):]
                break
        label = label[:16]
        n_runs = runs_per_model.get(model, "?") if runs_per_model else "?"
        cx = x + model_group_w // 2
        L.append(f'<text x="{cx}" y="12" text-anchor="middle" font-weight="bold" font-size="10">{label}</text>')
        L.append(f'<text x="{cx}" y="22" text-anchor="middle" font-size="7" class="dim" fill="#888">N={n_runs} runs</text>')
        if model_pass_rates and model in model_pass_rates:
            solved, total = model_pass_rates[model]
            pct = int(100 * solved / total) if total else 0
            pass_color = "#22c55e" if pct >= 60 else ("#f59e0b" if pct >= 30 else "#ef4444")
            L.append(f'<text x="{cx}" y="33" text-anchor="middle" font-size="7" fill="{pass_color}" font-weight="bold">{solved}/{total} solved ({pct}%)</text>')
        if model_averages and model in model_averages:
            avg = model_averages[model]
            L.append(f'<text x="{cx}" y="44" text-anchor="middle" font-size="7" class="dim" fill="#888">avg {avg:.2f}</text>')
        if model != model_names[0]:
            L.append(f'<line x1="{x}" y1="2" x2="{x}" y2="{h-3}" class="sep" stroke="#ccc" stroke-width="0.5"/>')
        x += model_group_w

    # Header row 2: sub-column labels
    x = task_col_w
    for _ in model_names:
        for i, label in enumerate(["score", "time", "tools"]):
            cx = x + sub_w * i + sub_w // 2
            L.append(f'<text x="{cx}" y="58" text-anchor="middle" class="dim" fill="#666" font-size="8">{label}</text>')
        x += model_group_w

    # Separator line below header
    L.append(f'<line x1="0" y1="{header_h-3}" x2="{w}" y2="{header_h-3}" class="sep" stroke="#ddd" stroke-width="0.5"/>')


    # Difficulty dot legend (top-right corner of task column)
    if task_difficulty:
        lx = task_col_w - 90
        for label, color in [("easy", "#22c55e"), ("medium", "#f59e0b"), ("hard", "#ef4444")]:
            L.append(f'<circle cx="{lx+4}" cy="10" r="3" fill="{color}" opacity="0.85"/>')
            L.append(f'<text x="{lx+10}" y="13" font-size="7" fill="#888">{label}</text>')
            lx += 38

    # Data rows
    _DIFF_COLOR = {"easy": "#22c55e", "medium": "#f59e0b", "hard": "#ef4444"}
    y = header_h
    for task in all_tasks:
        diff = (task_difficulty or {}).get(task)
        if diff:
            dot_color = _DIFF_COLOR[diff]
            L.append(f'<circle cx="7" cy="{y + 16}" r="4" fill="{dot_color}" opacity="0.8"/>')
            L.append(f'<text x="15" y="{y + 18}" font-size="9">{task}</text>')
        else:
            L.append(f'<text x="4" y="{y + 18}" font-size="9">{task}</text>')

        # Collect values across models for this task (mean, std, N)
        scores, times, tools = [], [], []
        score_ns, time_ns, tool_ns = [], [], []
        score_stds, time_stds, tool_stds = [], [], []
        for model in model_names:
            td = model_stats.get(model, {}).get(task)
            if td:
                scores.append(_mean(td["scores"]) if td.get("scores") else None)
                score_stds.append(_std(td["scores"]) if td.get("scores") and len(td["scores"]) >= 2 else 0)
                score_ns.append(len(td["scores"]) if td.get("scores") else 0)
                times.append(_mean(td["times"]) if td.get("times") else None)
                time_stds.append(_std(td["times"]) if td.get("times") and len(td["times"]) >= 2 else 0)
                time_ns.append(len(td["times"]) if td.get("times") else 0)
                tools.append(_mean(td["calls"]) if td.get("calls") else None)
                tool_stds.append(_std(td["calls"]) if td.get("calls") and len(td["calls"]) >= 2 else 0)
                tool_ns.append(len(td["calls"]) if td.get("calls") else 0)
            else:
                scores.append(None); score_stds.append(0); score_ns.append(0)
                times.append(None); time_stds.append(0); time_ns.append(0)
                tools.append(None); tool_stds.append(0); tool_ns.append(0)

        # t-value for 95% CI with N=3 (df=2)
        _T_VAL = 4.303

        def _ci_margin(sd, n):
            """95% CI margin: t * sd / sqrt(n). Returns 0 if no variance."""
            if sd < 0.001 or n < 2:
                return 0.0
            return _T_VAL * sd / math.sqrt(n)

        x = task_col_w
        y_mean = y + 14
        y_pm = y + 24
        for i, model in enumerate(model_names):
            sc, tm, tl = scores[i], times[i], tools[i]
            sc_sd, tm_sd, tl_sd = score_stds[i], time_stds[i], tool_stds[i]
            sc_n = len(model_stats.get(model_names[i], {}).get(task, {}).get("scores", []))
            tm_n = len(model_stats.get(model_names[i], {}).get(task, {}).get("times", []))
            tl_n = len(model_stats.get(model_names[i], {}).get(task, {}).get("calls", []))

            def _cell(cx, val, sd, n, all_vals, higher_is_better, fmt_val, fmt_margin,
                      abs_floor=None):
                if abs_floor is not None and val is not None and val < abs_floor:
                    # Absolute floor: always red regardless of relative rank
                    color = '#ffb3b3'
                else:
                    color = _row_relative_color(val, all_vals, higher_is_better=higher_is_better)
                L.append(f'<rect x="{cx+1}" y="{y+1}" width="{sub_w-2}" height="{row_h-2}" fill="{color}" rx="2"/>')
                L.append(f'<text class="cell" x="{cx+sub_w//2}" y="{y_mean}" text-anchor="middle" font-size="10">{fmt_val}</text>')
                margin = _ci_margin(sd, n)
                if margin > 0:
                    L.append(f'<text class="cell" x="{cx+sub_w//2}" y="{y_pm}" text-anchor="middle" font-size="7" fill="#555">±{fmt_margin(margin)}</text>')

            # Score — absolute floor: < 0.10 always red, never misleadingly green
            _cell(x, sc, sc_sd, sc_n, scores, True,
                  f"{sc:.2f}" if sc is not None else "-",
                  lambda m: f"{m:.2f}", abs_floor=0.10)
            # Time
            _cell(x + sub_w, tm, tm_sd, tm_n, times, False,
                  f"{tm:.0f}s" if tm is not None else "-",
                  lambda m: f"{m:.0f}s")
            # Tools
            _cell(x + sub_w * 2, tl, tl_sd, tl_n, tools, False,
                  f"{tl:.0f}" if tl is not None else "-",
                  lambda m: f"{m:.1f}")

            x += model_group_w
        y += row_h

    L.append('</svg>')
    return '\n'.join(L)


def _fmt_score(mean, std):
    if std > 0:
        return f"{mean:.4f} ±{std:.4f}"
    return f"{mean:.4f} ±0.0000"


def _fmt_time(mean, std):
    if std > 0:
        return f"{mean:.1f}s ±{std:.2f}s"
    return f"{mean:.1f}s ±0.00s"


def _fmt_calls(mean, std):
    if std > 0:
        return f"{mean:.0f} ±{std:.1f}"
    return f"{mean:.0f} ±0.0"


def discover_run_files(env_dir: Path) -> dict[str, list[dict]]:
    """Auto-discover {model}_run{N}.json files grouped by model.

    Returns: {"model_name": [run1_data, run2_data, ...]}
    Also checks for single dryrun-results.json as fallback.
    """
    models = defaultdict(list)

    # Pattern: {model}_run{N}.json
    for f in sorted(env_dir.glob("*_run*.json")):
        match = re.match(r"(.+)_run\d+\.json$", f.name)
        if match:
            model_name = match.group(1)
            try:
                data = json.loads(f.read_text())
                models[model_name].append(data)
            except (json.JSONDecodeError, OSError):
                continue

    # Fallback: single dryrun-results.json
    if not models:
        for name in ["dryrun-results.json", "dryrun_results.json"]:
            path = env_dir / name
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    models["baseline"] = [data]
                except (json.JSONDecodeError, OSError):
                    pass
                break

    return dict(models)


def _load_scoring_config(env_dir: Path) -> dict:
    """Load optional scoring config from env root.

    If scoring_display.json exists, it controls efficiency penalty settings.
    If not, defaults apply (penalty enabled, 15% max, 15 tool cap).

    Example scoring_display.json:
    {
        "efficiency_penalty": true,
        "penalty_weight": 0.15,
        "max_tools": 15,
        "sort_models": "score_desc"
    }
    """
    config_path = env_dir / "scoring_display.json" if env_dir else None
    if config_path and config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _apply_efficiency_penalty(score, tools, max_tools=15, penalty_weight=0.15):
    """Apply tool efficiency penalty to solved tasks.

    Models that solve a task in fewer tool calls keep more of their base score.
    Only applies when base score > 0.3 (task was meaningfully attempted).
    Max penalty: penalty_weight reduction for using max_tools or more.
    """
    if penalty_weight <= 0 or score < 0.3 or tools is None:
        return score
    tool_fraction = min(tools / max_tools, 1.0)
    return score * (1.0 - penalty_weight * tool_fraction)


# Module-level config, set per env in build_performance_table
_SCORING_CONFIG = {}


def aggregate_stats(runs: list[dict]) -> dict[str, dict]:
    """Aggregate per-task stats across multiple runs.

    Applies efficiency penalty if enabled in scoring config.

    Returns: {task_name: {"scores": [...], "times": [...], "calls": [...],
                          "best_run": {...}, "worst_run": {...}}}
    """
    enabled = _SCORING_CONFIG.get("efficiency_penalty", True)
    weight = _SCORING_CONFIG.get("penalty_weight", 0.15)
    max_tools = _SCORING_CONFIG.get("max_tools", 15)

    task_data = defaultdict(lambda: {"scores": [], "times": [], "calls": [], "runs": []})

    for run in runs:
        for result in run.get("results", []):
            task = result.get("task", "unknown")
            score = result.get("score")
            tools = result.get("tool_calls_total")
            if isinstance(score, (int, float)):
                if enabled:
                    adjusted = _apply_efficiency_penalty(score, tools, max_tools, weight)
                else:
                    adjusted = score
                task_data[task]["scores"].append(adjusted)
            time_s = result.get("time_seconds")
            if isinstance(time_s, (int, float)):
                task_data[task]["times"].append(time_s)
            calls = result.get("tool_calls_total")
            if isinstance(calls, (int, float)):
                task_data[task]["calls"].append(calls)
            task_data[task]["runs"].append(result)

    return dict(task_data)


def build_performance_table(all_models: dict[str, list[dict]], env_dir: Path = None) -> str:
    """Build markdown performance section from multi-run multi-model data."""
    if not all_models:
        return ""

    # Load scoring config (efficiency penalty toggle, model sort order)
    global _SCORING_CONFIG
    _SCORING_CONFIG = _load_scoring_config(env_dir) if env_dir else {}

    model_stats = {}
    total_runs = 0
    for model, runs in all_models.items():
        model_stats[model] = aggregate_stats(runs)
        total_runs += len(runs)

    # Collect all task names across all models
    all_tasks_set = set()
    for stats in model_stats.values():
        all_tasks_set.update(stats.keys())

    if not all_tasks_set:
        return ""

    # Compute per-task mean score across all models (needed for sort + difficulty)
    task_means = {}
    for task in all_tasks_set:
        all_scores = []
        for stats in model_stats.values():
            td = stats.get(task)
            if td and td.get("scores"):
                all_scores.extend(td["scores"])
        task_means[task] = _mean(all_scores) if all_scores else 0.0

    # Sort tasks by mean score descending: easy (high score) at top, hard (low) at bottom.
    # Falls back to alphabetical within ties.
    all_tasks = sorted(all_tasks_set, key=lambda t: (-task_means[t], t))

    model_names = list(all_models.keys())
    runs_per_model = {m: len(runs) for m, runs in all_models.items()}

    # Sort models: strongest (highest avg score) on left, weakest on right
    sort_mode = _SCORING_CONFIG.get("sort_models", "score_desc")
    if sort_mode == "score_desc":
        def _model_avg(m):
            stats = model_stats.get(m, {})
            all_scores = [s for td in stats.values() for s in td.get("scores", [])]
            return _mean(all_scores) if all_scores else 0
        model_names.sort(key=_model_avg, reverse=True)

    # Classify difficulty using tertile split (bottom third = hard, top third = easy).
    # Fully data-driven: thresholds are computed per-env from actual run scores,
    # so the distribution is always meaningful regardless of absolute score level.
    sorted_means = sorted(task_means.values())
    n = len(sorted_means)
    hard_thresh = sorted_means[max(0, n // 3 - 1)] if n >= 3 else 0
    easy_thresh = sorted_means[min(n - 1, (2 * n) // 3)] if n >= 3 else 1
    task_difficulty = {}
    for t in all_tasks:
        m = task_means[t]
        if m >= easy_thresh:
            task_difficulty[t] = "easy"
        elif m <= hard_thresh:
            task_difficulty[t] = "hard"
        else:
            task_difficulty[t] = "medium"
    easy_count = sum(1 for d in task_difficulty.values() if d == "easy")
    medium_count = sum(1 for d in task_difficulty.values() if d == "medium")
    hard_count = sum(1 for d in task_difficulty.values() if d == "hard")
    difficulty_counts = {
        "total": len(all_tasks), "easy": easy_count, "medium": medium_count, "hard": hard_count
    }

    # Compute global averages for time estimate
    all_times = []
    for stats in model_stats.values():
        for td in stats.values():
            all_times.extend(td["times"])
    avg_time = _mean(all_times) if all_times else 30.0

    # Detect domain for workflow example
    if env_dir is None:
        env_dir = Path(".")
    student_dir = env_dir / "student_data"
    has_rl_wrapper = (env_dir / "rl_wrapper.sh").exists()
    has_k8s = (env_dir / "k8s-rl-job.yaml").exists()
    domain = "generic"
    if student_dir.is_dir():
        exts = {f.suffix for f in student_dir.rglob("*") if f.is_file()}
        if ".lean" in exts:
            domain = "lean"
        elif ".go" in exts:
            domain = "go"
        elif ".py" in exts:
            domain = "python"

    workflow_examples = {
        "lean": [
            "1. `bash: cat /workdir/data/MyTheorem.lean` to read the file",
            "2. `replace_in_file` to replace `sorry` with a valid proof",
            "3. `bash: lean /workdir/data/MyTheorem.lean` to compile and check for errors",
            "4. Read errors, fix, repeat until clean compilation",
        ],
        "go": [
            "1. `bash: cat /workdir/data/consensus/my_file.go` to read the buggy code",
            "2. `replace_in_file` to fix the bug",
            "3. `bash: cd /workdir/data/consensus && go test .` to run tests",
            "4. Read failures, fix, repeat until tests pass",
        ],
        "python": [
            "1. `bash: cat /workdir/data/my_module.py` to read the code",
            "2. `replace_in_file` to fix or implement the logic",
            "3. `bash: cat /workdir/data/my_module.py` to verify the edit",
        ],
        "generic": [
            "1. Read the task file in `/workdir/data/`",
            "2. Edit it using `replace_in_file`",
            "3. Verify using `bash`",
        ],
    }

    lines = [
        "## Student Tools",
        "",
        "The student agent operates in a sandboxed bash environment with three tools:",
        "",
        "| Tool | What it does |",
        "|------|-------------|",
        "| `bash` | Run shell commands. Read files, run tests, check output. |",
        "| `view_lines_in_file` | Read specific line ranges from a file. |",
        "| `replace_in_file` | Edit a file by replacing an exact string match. |",
        "",
        "The student can read `/workdir/data/` (workspace) and `/workdir/shared/` (reference). It cannot read `/root_data/` (scoring, configs).",
        "",
        "Typical workflow:",
        "",
        *workflow_examples.get(domain, workflow_examples["generic"]),
        "",
        "## Setup",
        "",
        "Requires Docker. No GPU or special hardware.",
        "",
        "```bash",
        "./run.sh build    # build the scoring container",
        "./run.sh list     # list available tasks",
        "```",
        "",
        *([
            "## RL Training Integration",
            "",
            "### Docker",
            "",
            "```bash",
            "./rl_wrapper.sh . <task_id> /tmp/student_workspace",
            "# Returns JSON: {\"score\": 0.73, \"metadata\": {...}}",
            "```",
            "",
            *(["### Kubernetes",
               "",
               "Drop all egress from scoring pods via `NetworkPolicy`.",
               "",
               "```bash",
               "kubectl apply -f k8s-rl-job.yaml",
               "kubectl logs job/rl-episode",
               "```",
               ""] if has_k8s else []),
        ] if has_rl_wrapper else []),
        "## Security Model",
        "",
        "| Path | Access | Contents |",
        "|------|--------|----------|",
        "| `/root_data/` | Root only (0700) | Scoring scripts, eval configs |",
        "| `/workdir/shared/` | Read-only | Reference material |",
        "| `/workdir/data/` | Read/write | Student workspace |",
        "",
        "Production: `read_only: true`, `network_mode: none`, `cap_drop: ALL`, `no-new-privileges`.",
        "",
        "## Baseline Results",
        "",
        f"Evaluated {len(all_tasks)} tasks across {', '.join(model_names)}.",
        "",
        "### Reproduce",
        "",
        "See **Running Evaluations & Updating the Scorecard** above for the full workflow including API keys and model ID strings.",
        "",
        "```bash",
        "./run.sh build",
        "python3 /path/to/env-builder/dryrun.py . --all-tasks --model <model> --output <model>_run1.json",
        "./update_results.sh",
        "```",
        "",
        f"Takes ~{int(avg_time * len(all_tasks) * 1.2)}s on 8-core CPU.",
        "",
        "",
        "### Final Score Sheet",
        "",
    ]

    # Run count info
    run_counts = [f"{m} (N={n})" for m, n in runs_per_model.items()]
    lines.append(f"*{', '.join(run_counts)} evaluation runs. The `±` values show the standard deviation across runs.*")
    lines.append("")

    # Compute per-model pass rates and averages for heatmap header + average row
    _PASS_FLOOR = 0.10
    model_pass_rates = {}
    model_averages = {}
    for model in model_names:
        stats = model_stats.get(model, {})
        task_means_for_model = []
        solved = 0
        for task in all_tasks:
            td = stats.get(task)
            if td and td.get("scores"):
                mean = _mean(td["scores"])
                task_means_for_model.append(mean)
                if mean >= _PASS_FLOOR:
                    solved += 1
        model_pass_rates[model] = (solved, len(all_tasks))
        model_averages[model] = _mean(task_means_for_model) if task_means_for_model else 0.0

    # Generate unified heatmap SVG (replaces markdown table)
    # Colors are relative per row: best=green, worst=red within each task
    # Score: higher is better. Time/tools: lower is better.
    if env_dir:
        svg = generate_heatmap_svg(model_stats, model_names, all_tasks,
                                   runs_per_model=runs_per_model,
                                   task_difficulty=task_difficulty,
                                   model_pass_rates=model_pass_rates,
                                   model_averages=model_averages)
        svg_path = env_dir / "scores.svg"
        svg_path.write_text(svg)
        lines.append("#### Performance Heatmap")
        lines.append("")
        diff_line = (f"**Difficulty:** {easy_count} easy &nbsp;·&nbsp; {medium_count} medium"
                     f" &nbsp;·&nbsp; {hard_count} hard"
                     f" &emsp; *(tertile split by mean score across all models — updates with new runs)*")
        lines.append(diff_line)
        lines.append("")
        lines.append("**How to read this table:**")
        lines.append("- **Score**: final reward signal [0, 1]. Includes a tool efficiency penalty: models that solve a task in fewer tool calls keep more of their base score (up to 15% reduction at 15+ calls). Green = highest in the row.")
        lines.append("- **Time**: seconds to complete. Green = fastest in the row.")
        lines.append("- **Tools**: tool calls (bash, file read, file edit) before submission. Fewer is better. Affects the score via efficiency penalty.")
        lines.append("- **±**: 95% confidence interval. No ± means identical results every run.")
        lines.append("- Green = best. Red = worst. Yellow = middle. Colors compare models within each row.")
        lines.append("")
        lines.append("![Performance heatmap](scores.svg)")

    # Example SD calculation: pick the first task with non-zero std
    sd_example = _build_sd_example(model_stats, model_names, all_tasks)
    if sd_example:
        lines.append("")
        lines.append(sd_example)

    # Example agent execution (best + worst from first model with data)
    example_section = _build_example_section(model_stats, model_names)
    if example_section:
        lines.append("")
        lines.extend(example_section)

    return "\n".join(lines), difficulty_counts


def _build_sd_example(model_stats, model_names, all_tasks):
    """Build a concrete SD calculation example from actual run data."""
    for model in model_names:
        for task in all_tasks:
            td = model_stats[model].get(task)
            if not td or len(td["scores"]) < 2:
                continue
            scores = td["scores"]
            sd = _std(scores)
            if sd < 0.0001:
                continue
            mean = _mean(scores)
            n = len(scores)
            scores_str = ", ".join(f"{s:.4f}" for s in scores)
            diffs_str = ", ".join(f"({s:.4f} - {mean:.4f})²" for s in scores[:3])
            if len(scores) > 3:
                diffs_str += ", ..."
            margin = 4.303 * sd / (n ** 0.5)
            return (
                f"**Example: how ±{margin:.2f} was computed for `{task}` ({model}, N={n})**\n"
                f"> Scores across {n} runs: [{scores_str}]\n"
                f"> Mean = {mean:.4f}, SD = {sd:.4f}, 95% CI margin = 4.303 * {sd:.4f} / sqrt({n}) = {margin:.2f}"
            )
    return None


def _build_example_section(model_stats, model_names):
    """Build example agent execution section.

    Picks the best result from the strongest model and the worst
    result from the weakest model. Shows the full range of outcomes.
    """
    lines = []

    # Collect best and worst across ALL models
    global_best = None
    global_best_model = None
    global_worst = None
    global_worst_model = None

    for model in model_names:
        stats = model_stats[model]
        all_runs = []
        for td in stats.values():
            all_runs.extend(td["runs"])
        valid = [r for r in all_runs if r.get("score") is not None]
        if not valid:
            continue

        best = max(valid, key=lambda x: (x.get("score", 0), "scoring_metadata" in x))
        worst = min(valid, key=lambda x: (x.get("score", 0), "scoring_metadata" not in x))

        if global_best is None or best.get("score", 0) > global_best.get("score", 0):
            global_best = best
            global_best_model = model
        if global_worst is None or worst.get("score", 0) < global_worst.get("score", 0):
            global_worst = worst
            global_worst_model = model

    if not global_best:
        return lines

    best_score = global_best.get("score", 0)
    worst_score = global_worst.get("score", 0)

    # Use the best model's name for the section header
    model = global_best_model

    lines.append(f"### Example Agent Execution")
    lines.append("")

    if best_score > 0:
        lines.extend(_format_run(global_best, f"Successful Execution ({global_best_model})"))
    if worst_score < 1.0 and global_worst.get("task") != global_best.get("task"):
        lines.extend(_format_run(global_worst, f"Failed Execution ({global_worst_model})"))

    return lines


def _format_run(res, title):
    score = res.get("score", 0)
    task = res.get("task", "unknown")
    md = [f"#### {title} (`{task}`)", "", f"**Final Score:** {score:.4f}"]

    meta = res.get("scoring_metadata", {})
    if meta:
        md.append("**Score Calculation:**")
        md.append("```json")
        clean_meta = {k: v for k, v in meta.items() if v != "" and v != []}
        md.append(json.dumps(clean_meta, indent=2))
        md.append("```")

        if "base_completeness_score" in meta and "sorry_penalty" in meta:
            b = meta.get("base_completeness_score", 0.0)
            p = meta.get("sorry_penalty", 1.0)
            md.append(f"**Formula:** `base_completeness_score ({b}) * sorry_penalty ({p}) = {score:.4f}`")
        elif "pass_rate" in meta:
            pr = meta.get("pass_rate", 0.0)
            center = meta.get("sigmoid_center", 0.5)
            scale = meta.get("sigmoid_scale", 8.0)
            z = scale * (pr - center)
            md.append(f"**Formula:** `sigmoid({scale} * ({pr} - {center})) = {score:.4f}`")
        else:
            md.append(f"**Formula:** `Aggregate Score = {score:.4f}`")

    md.append("")

    strat = res.get("student_strategy", "").strip()
    if strat:
        strat_clean = strat.replace("\n", " ").replace("  ", " ")
        md.append("**Agent Strategy:**")
        md.append(f"> {strat_clean[:300]}...")
        md.append("")

    calls = res.get("tool_calls_summary", [])
    if calls:
        md.append("**Tool Call Chain:**")
        for c in calls[:5]:
            c_clean = c.replace("\n", " ")
            md.append(f"1. `{c_clean}`")
        if len(calls) > 5:
            md.append(f"1. ... ({len(calls) - 5} more calls)")
        md.append("")

    md.append("---")
    md.append("")
    return md


def update_readme(env_dir: Path, new_sections: list[str], difficulty_counts: dict = None):
    """Append or replace sections in README.md.

    difficulty_counts: optional {"total": N, "easy": E, "medium": M, "hard": H}
    If provided, updates the '| Tasks | ... |' row in the Overview table.
    """
    readme = env_dir / "README.md"
    if not readme.exists():
        readme.write_text("\n\n".join(new_sections) + "\n")
        return

    content = readme.read_text()

    # Update Tasks row in Overview table with difficulty counts
    if difficulty_counts and difficulty_counts.get("total"):
        n = difficulty_counts["total"]
        e = difficulty_counts["easy"]
        m = difficulty_counts["medium"]
        h = difficulty_counts["hard"]
        tasks_val = f"{n} ({e} easy · {m} medium · {h} hard)"
        content = re.sub(
            r'(\|\s*Tasks\s*\|)[^|\n]+(\|)',
            lambda mo: f"{mo.group(1)} {tasks_val} {mo.group(2)}",
            content,
            count=1,
        )

    # Remove existing auto-generated sections
    markers = ["## Student Tools", "## Setup and Quick Start", "## Setup",
               "## Running the RL Training Loop", "## RL Training Integration",
               "## Security", "## Security Model", "## Baseline Performance",
               "## Baseline Results", "## Difficulty Assessment", "**Score distribution:**"]
    for marker in markers:
        if marker in content:
            idx = content.index(marker)
            rest = content[idx + len(marker):]
            next_section = rest.find("\n## ")
            if next_section >= 0:
                content = content[:idx] + content[idx + len(marker) + next_section + 1:]
            else:
                content = content[:idx].rstrip()

    content = content.rstrip() + "\n\n" + "\n\n".join(new_sections) + "\n"
    readme.write_text(content)


def main():
    if len(sys.argv) < 2:
        print("Usage: finalize_readme.py <env-dir> [--model MODEL]")
        sys.exit(1)

    env_dir = Path(sys.argv[1])

    all_models = discover_run_files(env_dir)
    if not all_models:
        print("No run result files found. Expected {model}_run{N}.json or dryrun-results.json.")
        sys.exit(1)

    print(f"Discovered {sum(len(v) for v in all_models.values())} runs across {len(all_models)} models: {list(all_models.keys())}")

    sections = []
    difficulty_counts = {}
    result = build_performance_table(all_models, env_dir=env_dir)
    if result:
        table, difficulty_counts = result
        sections.append(table)

    if not sections:
        print("No results to add to README.")
        sys.exit(0)

    update_readme(env_dir, sections, difficulty_counts=difficulty_counts)
    print(f"README.md updated with {len(sections)} sections")


if __name__ == "__main__":
    main()
