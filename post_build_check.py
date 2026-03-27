#!/usr/bin/env python3
"""Post-build deterministic checks for environment quality.

Run after building to catch issues before deployment.
Catches issues that would cause failures at runtime.

Exit 0 = pass, exit 1 = issues found (printed to stdout).
"""

import json
import os
import re
import sys
from pathlib import Path


def check(env_dir: str) -> list[str]:
    env = Path(env_dir)
    issues = []

    # 1. README exists and follows template structure
    readme = env / "README.md"
    if not readme.exists():
        issues.append("MISSING: README.md — generate from README_TEMPLATE.md")
    else:
        content = readme.read_text()
        required_sections = ["## Overview", "## Scoring", "## What the Student"]
        for section in required_sections:
            if section not in content:
                issues.append(f"README: missing section '{section}'")
        if len(content.split("\n")) > 350:
            issues.append(f"README: too long ({len(content.split(chr(10)))} lines, target <80)")

    # 2. Task count check
    tasks_dir = env / "src" / "environment" / "tasks"
    if tasks_dir.exists():
        task_dirs = [d for d in tasks_dir.iterdir() if d.is_dir() and not d.name.startswith("_") and d.name != "__pycache__"]
        if len(task_dirs) < 1:
            issues.append(f"TASKS: only {len(task_dirs)} tasks (need at least 1)")

        # 3. No dots in directory names
        for d in task_dirs:
            if "." in d.name:
                issues.append(f"TASK DIR: '{d.name}' contains dots — Python cannot import this")

    # 4. Scoring.py is standalone (has subprocess or server management)
    scoring_candidates = list(env.glob("root_data/**/scoring.py"))
    if scoring_candidates:
        scoring_code = scoring_candidates[0].read_text()
        if "def compute_score" not in scoring_code:
            issues.append("SCORING: no compute_score() function")
        if "def main" not in scoring_code:
            issues.append("SCORING: no main() function")

    # 5. Eval configs exist and are valid JSON
    config_dir = env / "root_data" / "eval" / "configs"
    if not config_dir.exists():
        issues.append("CONFIGS: root_data/eval/configs/ directory missing")
    else:
        configs = list(config_dir.glob("*.json"))
        if len(configs) == 0:
            issues.append("CONFIGS: no eval config JSON files")
        for cfg in configs:
            try:
                json.loads(cfg.read_text())
            except json.JSONDecodeError:
                issues.append(f"CONFIG: invalid JSON in {cfg.name}")

    # 6. Containerfile checks
    containerfile = env / "Containerfile"
    if containerfile.exists():
        cf = containerfile.read_text()
        cf_lines = cf.strip().split("\n")
        iptables_pos = cf.find("iptables")
        user_student_pos = cf.find("USER student")
        prod_compose_text = (env / "docker-compose.prod.yml").read_text() if (env / "docker-compose.prod.yml").exists() else ""
        if iptables_pos == -1 and "network_mode" not in prod_compose_text:
            issues.append("CONTAINERFILE: no iptables network block and no network_mode in docker-compose.prod.yml")
        if user_student_pos != -1 and iptables_pos != -1 and iptables_pos > user_student_pos:
            issues.append("CONTAINERFILE: iptables appears AFTER USER student — network block may not work")
        # Final USER must be student (not root)
        last_user = None
        for line in cf_lines:
            stripped = line.strip()
            if stripped.startswith("USER "):
                last_user = stripped.split()[1]
        if last_user != "student":
            issues.append(f"CONTAINERFILE: final USER is '{last_user}' — must be 'student' (scoring uses --user root)")

    # 7. Task prompts include iteration workflow
    if tasks_dir.exists():
        has_iteration = 0
        for d in task_dirs:
            init = d / "__init__.py"
            if init.exists():
                code = init.read_text()
                # Check base class or task itself mentions test/compile/iterate
                if any(kw in code.lower() for kw in ["test_kernel", "test_serve", "run_benchmark", "compile", "iterate", "workflow"]):
                    has_iteration += 1
        # Check _base.py for iteration suffix
        base = tasks_dir / "_base.py"
        if base.exists():
            base_code = base.read_text()
            if any(kw in base_code.lower() for kw in ["iterate", "test your", "workflow", "compile your"]):
                has_iteration = len(task_dirs)  # base handles it for all
        if has_iteration == 0:
            issues.append("PROMPTS: no task mentions iteration/testing workflow — students won't know to self-test")

    # 8. Student data has content (not just .gitkeep)
    student_dir = env / "student_data"
    if student_dir.exists():
        real_files = [f for f in student_dir.rglob("*") if f.is_file() and f.name != ".gitkeep"]
        if len(real_files) < 3:
            issues.append(f"STUDENT DATA: only {len(real_files)} real files (need reference implementations, configs, etc.)")

    # 9. run.sh, docker-compose, and dryrun.py exist (plug-and-play for customers)
    if not (env / "run.sh").exists():
        issues.append("MISSING: run.sh — customers need this for quick build/test/shell commands")
    if not (env / "docker-compose.yml").exists():
        issues.append("MISSING: docker-compose.yml — customers need this for docker compose workflow")
    if not (env / "docker-compose.prod.yml").exists():
        issues.append("MISSING: docker-compose.prod.yml — needed for production security (read-only, no network)")
    if not (env / "dryrun.py").exists():
        issues.append("MISSING: dryrun.py — customers need this for automated testing (scores via Docker)")

    # 10. docker-compose.prod.yml has /home/student tmpfs when read_only is set
    prod_compose = env / "docker-compose.prod.yml"
    if prod_compose.exists():
        pc = prod_compose.read_text()
        if "read_only: true" in pc and "/home/student" not in pc:
            issues.append("COMPOSE PROD: read_only is true but no /home/student tmpfs — Python/tool caches will crash")

    # 11. run.sh and dryrun.py use --user root for scoring commands
    runsh = env / "run.sh"
    if runsh.exists():
        rs = runsh.read_text()
        # Find docker run lines that touch /root_data (scoring/list) but lack --user root
        for i, line in enumerate(rs.split("\n"), 1):
            if "docker run" in line and "root_data" in line and "--user root" not in line:
                # Check next few lines too (multi-line commands)
                chunk = "\n".join(rs.split("\n")[max(0,i-2):i+3])
                if "--user root" not in chunk:
                    issues.append(f"RUN.SH: docker run accesses /root_data but missing --user root (line ~{i})")
                    break
    dryrun = env / "dryrun.py"
    if dryrun.exists():
        dp = dryrun.read_text()
        if "/root_data/" in dp and '"--user", "root"' not in dp and "--user root" not in dp:
            issues.append("DRYRUN.PY: accesses /root_data in Docker but missing --user root")

    # 12. Configs referencing data files that don't exist in the repo
    config_dir = env / "root_data" / "eval" / "configs"
    if config_dir.exists():
        for cfg in config_dir.glob("*.json"):
            try:
                c = json.loads(cfg.read_text())
            except json.JSONDecodeError:
                continue
            # Check eval_prompts_path
            prompts_path = c.get("eval_prompts_path", "")
            if prompts_path:
                # Map container path to repo path
                repo_path = env / prompts_path.lstrip("/")
                if not repo_path.exists():
                    issues.append(f"DATA: config {cfg.name} references {prompts_path} but file missing from repo")
                    break  # One warning is enough
            # Check reference_model_path
            model_path = c.get("reference_model_path", "")
            if model_path:
                repo_model = env / model_path.lstrip("/")
                # Models might be downloaded at build time — check if Containerfile handles it
                cf = env / "Containerfile"
                if cf.exists():
                    cf_text = cf.read_text()
                    model_name = Path(model_path).name
                    if not repo_model.exists() and "huggingface-cli" not in cf_text and model_name not in cf_text:
                        issues.append(f"DATA: config {cfg.name} references model {model_path} but not in repo and no download in Containerfile")
                        break

    # 13. README Quick Start matches env reality
    readme = env / "README.md"
    containerfile = env / "Containerfile"
    if readme.exists():
        readme_text = readme.read_text().lower()

        # If env needs HF models, README must mention HF_TOKEN
        if containerfile.exists():
            cf_text = containerfile.read_text()
            if "huggingface-cli" in cf_text or "HF_TOKEN" in cf_text:
                if "hf_token" not in readme_text and "huggingface" not in readme_text:
                    issues.append("README: Containerfile downloads HF models but README doesn't mention HF_TOKEN setup")

            # If env needs GPU, README must mention nvidia/GPU
            if "nvidia" in cf_text.lower() or "cuda" in cf_text.lower() or "runtime: nvidia" in cf_text.lower():
                if "gpu" not in readme_text and "nvidia" not in readme_text:
                    issues.append("README: Containerfile needs GPU but README doesn't mention GPU requirements")

            # If env needs TPU, README must mention TPU
            if "tpu" in cf_text.lower() or "elan" in cf_text.lower():
                # elan = lean, not TPU. Only flag for actual TPU
                if "tpu" in cf_text.lower() and "tpu" not in readme_text:
                    issues.append("README: Containerfile needs TPU but README doesn't mention TPU requirements")

        # README must have Quick Start or Getting Started
        if "quick start" not in readme_text and "getting started" not in readme_text and "## setup" not in readme_text:
            issues.append("README: no Quick Start or Getting Started section — customers won't know how to begin")

        # README must mention run.sh or docker
        if "run.sh" not in readme_text and "docker" not in readme_text:
            issues.append("README: doesn't mention run.sh or docker commands — customers won't know how to use it")

    # 14. Prerequisites section exists if hardware is needed
    if containerfile.exists() and readme.exists():
        cf_text = containerfile.read_text().lower()
        readme_text = readme.read_text().lower()
        needs_hardware = "nvidia" in cf_text or "tpu" in cf_text or "cuda" in cf_text
        has_prereqs = "prerequisit" in readme_text or "requirements" in readme_text.split("## quick")[0] if "quick" in readme_text else False
        if needs_hardware and not has_prereqs:
            issues.append("README: env needs special hardware but no Prerequisites section before Quick Start")

    # 15. Anti-Stub Check for validation scripts
    validate_script = env / "root_data" / "validate_harness.py"
    if validate_script.exists():
        code = validate_script.read_text()
        if "subprocess" not in code and "compute_score" not in code and "docker" not in code:
            issues.append("VALIDATION: validate_harness.py does not appear to execute any external harness or scoring functions (stubbed?)")
        
        # Check for unconditional sys.exit(0) as the only logic path
        if code.strip().endswith("sys.exit(0)") and "if " not in code:
             issues.append("VALIDATION: validate_harness.py appears to unconditionally pass without checks")

    # 16. Anti-AI-Slop Check for README
    if readme.exists():
        readme_text = readme.read_text().lower()
        forbidden_slop = [
            "seamlessly", "perfectly", "delve", "testament", "robustly", 
            "llm agent", "ai agent", "unprecedented", "game-changing", 
            "revolutionary", "cutting-edge", "state-of-the-art", 
            "tailored", "leverage", "empower"
        ]
        for word in forbidden_slop:
            if word in readme_text:
                issues.append(f"README: contains forbidden AI-slop or banned phrasing: '{word}'")

        # Super basic emoji detection (looking for common AI emojis)
        if "🚀" in readme_text or "✨" in readme_text or "🔥" in readme_text or "💡" in readme_text:
            issues.append("README: contains unprofessional emojis (e.g. rocket, sparkles). Keep it strictly technical.")

    # 17. Leftover TODOs
    for file in env.rglob("*.py"):
        if file.name == "post_build_check.py":
            continue
        if "TODO:" in file.read_text():
            issues.append(f"TODO: Leftover placeholder found in {file.name}")
    for file in env.rglob("*.md"):
        if "TODO:" in file.read_text():
            issues.append(f"TODO: Leftover placeholder found in {file.name}")
    # 17. Kubernetes Template Check
    k8s_job = env / "k8s-rl-job.yaml"
    if k8s_job.exists():
        k8s_text = k8s_job.read_text()
        if "YOUR_ENV_IMAGE_NAME" in k8s_text:
            issues.append("KUBERNETES: k8s-rl-job.yaml still contains placeholder 'YOUR_ENV_IMAGE_NAME'. Replace it with the actual image name.")
        if "YOUR_TASK_ID" in k8s_text:
            issues.append("KUBERNETES: k8s-rl-job.yaml still contains placeholder 'YOUR_TASK_ID'. Replace it with a valid default task ID.")

    # 18. Lean Mathlib Dependency Check
    lean_files = list(env.rglob("*.lean"))
    if lean_files and containerfile.exists():
        cf_text = containerfile.read_text()
        needs_mathlib = False
        for lf in lean_files:
            try:
                if "import Mathlib" in lf.read_text():
                    needs_mathlib = True
                    break
            except Exception:
                pass
        if needs_mathlib:
            if "lake" not in cf_text.lower() and "mathlib" not in cf_text.lower():
                issues.append("DEPENDENCIES: A Lean task imports 'Mathlib', but the Containerfile does not appear to install or build Mathlib. The task is unsolvable.")

    # 19. TTY Safety and Interactive Command Check
    for file in env.rglob("*"):
        if not file.is_file() or file.suffix not in (".py", ".sh", ".yaml", ".yml", ""):
            continue
        if file.name == "post_build_check.py":
            continue
        try:
            content = file.read_text()
            # Check for sudo
            if re.search(r'\bsudo\s', content):
                issues.append(f"TTY SAFETY: Interactive 'sudo' command found in {file.relative_to(env)}. This will hijack the host TTY and hang the pipeline.")
            
            # Check for apt-get without -y
            if "apt-get install" in content and "-y" not in content:
                issues.append(f"TTY SAFETY: 'apt-get install' without '-y' found in {file.relative_to(env)}. This will hang waiting for user prompt.")
            
            # Check for read -p
            if re.search(r'\bread -p\b', content):
                issues.append(f"TTY SAFETY: Interactive 'read -p' found in {file.relative_to(env)}. This will hang waiting for user input.")
                
            # Check subprocess.run safety in Python files
            if file.suffix == ".py" and "subprocess.run" in content:
                if file.name in ("dryrun.py", "scoring.py", "validate_harness.py"):
                    if "start_new_session=True" not in content and "subprocess.DEVNULL" not in content:
                        issues.append(f"TTY SAFETY: subprocess.run found in {file.relative_to(env)} without 'start_new_session=True' or 'stdin=subprocess.DEVNULL'. This can cause TTY hijacking if the agent uses interactive tools.")
        except Exception:
            pass
            
    # 20. Task Granularity / Token Economy Check
    student_data_dir = env / "student_data"
    if student_data_dir.exists():
        loc_count = 0
        for f in student_data_dir.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                try:
                    loc_count += len(f.read_text().splitlines())
                except Exception:
                    pass
        if loc_count > 5000:
            issues.append(f"TOKEN ECONOMY: student_data contains {loc_count} lines of text. This is too massive for raw RL context windows. Keep tasks algorithmic and focused (under 5000 lines).")

    return issues

def main():
    if len(sys.argv) < 2:
        print("Usage: post_build_check.py <env-dir>")
        sys.exit(1)

    issues = check(sys.argv[1])

    if len(issues) > 1:
        print(f"POST-BUILD CHECK: {len(issues)} issues found (FAILED - more than 1 allowed exception)")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    elif len(issues) == 1:
        print(f"POST-BUILD CHECK: 1 issue found (WARNING - permitted under 95% rule)")
        print(f"  - {issues[0]}")
        sys.exit(0)
    else:
        print("POST-BUILD CHECK: all passed")
        sys.exit(0)

if __name__ == "__main__":
    main()
