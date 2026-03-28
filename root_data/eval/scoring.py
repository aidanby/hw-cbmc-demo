#!/usr/bin/env python3
"""hw-cbmc formal hardware verification scorer.

Runs as root. Student cannot read this file.

Scoring architecture:
  1. Anti-cheat checks (ALL run BEFORE ebmc)
  2. EBMC invocation: count PROVED vs REFUTED properties
  3. Sigmoid scoring on proved_fraction

Formula:
  proved_fraction = num_proved / num_expected_properties
  base_score      = sigmoid(scale * (proved_fraction - center))
                    with scale=8.0, center=0.55
  cheat_penalty   = 1.0 if no cheating detected, else 0.0
  final_score     = base_score * cheat_penalty

Anti-cheat checks (in order, all run before EBMC):
  1. Property count:    fewer assert property/final lines than expected → 0
  2. Property names:    named assertions missing from file → 0
  3. Trivial assertions: assert property(1'b1) or assert final(1) → 0
  4. Module interface:  top-level module signature changed → 0
  5. $finish/$stop:     simulation halting commands → 0
  6. synthesis_off:     // synthesis translate_off → 0
  7. Assertion identity: named assertion body is (1)/(1'b1)/(|0)/(~0) → warn only
  8. Assume/restrict:   assume property / restrict (SV) or INVAR/TRANS/FAIRNESS (SMV) → 0
  9. Assertion body hash: SHA256 of all assertion lines must match config → 0

Usage:
    python scoring.py <config_path> <output_path>
"""

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path


# --- Scoring constants ---
SIGMOID_CENTER = 0.55
SIGMOID_SCALE = 8.0
DEFAULT_TIMEOUT = 30


def _safe_exp(x):
    try:
        return math.exp(x)
    except OverflowError:
        return float("inf") if x > 0 else 0.0


def compute_score(proved_fraction, *, center=None, scale=None):
    """Sigmoid scoring on proved_fraction.

    Calibration (center=0.55, scale=8.0):
        0.0 proved → ~0.03  (some score even for total failure)
        0.5 proved → ~0.35
        1.0 proved → ~0.97  (full score for complete fix)
    """
    if center is None:
        center = SIGMOID_CENTER
    if scale is None:
        scale = SIGMOID_SCALE

    if not math.isfinite(proved_fraction):
        return 0.0
    proved_fraction = max(0.0, min(1.0, proved_fraction))

    z = scale * (proved_fraction - center)
    raw = 1.0 / (1.0 + _safe_exp(-z))

    # Normalize: proved_fraction=1.0 → score ~1.0
    z_max = scale * (1.0 - center)
    raw_max = 1.0 / (1.0 + _safe_exp(-z_max))
    base_score = min(1.0, raw / raw_max) if raw_max > 0 else raw

    return round(min(1.0, max(0.0, base_score)), 6)


# ── Anti-cheat helpers ───────────────────────────────────────────────

def _strip_sv_comments(source: str) -> str:
    """Remove // line comments and /* */ block comments from SV source."""
    result = []
    i = 0
    in_line = False
    in_block = False
    while i < len(source):
        if in_line:
            if source[i] == '\n':
                in_line = False
                result.append('\n')
            i += 1
            continue
        if in_block:
            if source[i:i+2] == '*/':
                in_block = False
                i += 2
            else:
                if source[i] == '\n':
                    result.append('\n')
                i += 1
            continue
        if source[i:i+2] == '//':
            in_line = True
            i += 2
            continue
        if source[i:i+2] == '/*':
            in_block = True
            i += 2
            continue
        result.append(source[i])
        i += 1
    return ''.join(result)


def _strip_smv_comments(source: str) -> str:
    """Remove -- line comments from NuSMV source."""
    result = []
    for line in source.splitlines(keepends=True):
        # Strip everything after --
        idx = line.find('--')
        if idx >= 0:
            result.append(line[:idx] + '\n')
        else:
            result.append(line)
    return ''.join(result)


def _count_assert_lines(source: str, is_smv: bool = False) -> int:
    """Count assert property / assert final / LTLSPEC lines."""
    if is_smv:
        stripped = _strip_smv_comments(source)
        # NuSMV: LTLSPEC or CTLSPEC
        return len(re.findall(r'\b(?:LTLSPEC|CTLSPEC|INVARSPEC)\b', stripped))
    else:
        stripped = _strip_sv_comments(source)
        return len(re.findall(r'\bassert\s+(?:property|final)\b', stripped))


def _check_property_names(source: str, property_names: list, is_smv: bool = False) -> list:
    """Return list of expected property names missing from source."""
    if is_smv:
        stripped = _strip_smv_comments(source)
    else:
        stripped = _strip_sv_comments(source)
    missing = []
    for name in property_names:
        # Named SV assertions look like: p_reset: assert property (...)
        # We just check the label appears (word boundary)
        if not re.search(r'\b' + re.escape(name) + r'\b', stripped):
            missing.append(name)
    return missing


def _has_trivial_assertion(source: str, is_smv: bool = False) -> bool:
    """Check for tautological assertions that always pass."""
    if is_smv:
        stripped = _strip_smv_comments(source)
        # LTLSPEC G 1  or  LTLSPEC TRUE
        if re.search(r'\bLTLSPEC\s+(?:G\s+)?(?:TRUE|1)\b', stripped):
            return True
        return False
    else:
        stripped = _strip_sv_comments(source)
        # assert property (1'b1) / assert final (1) / assert property (1) / etc.
        trivial = [
            r"assert\s+property\s*\(\s*1'b1\s*\)",
            r"assert\s+final\s*\(\s*1\s*\)",
            r"assert\s+property\s*\(\s*1\s*\)",
            r"assert\s+property\s*\(\s*\$sampled\s*\(\s*1\s*\)\s*\)",
            r"assert\s+property\s*\(\s*1'b1\s*\)",
        ]
        for pattern in trivial:
            if re.search(pattern, stripped):
                return True
        return False


def _check_module_signature(source: str, expected_sig: str) -> bool:
    """Check if top-level module signature matches expected (token-by-token, ignoring whitespace)."""
    # Extract the first module declaration
    m = re.search(r'module\s+\w+\s*\([^)]*\)', source)
    if not m:
        return False
    actual = ' '.join(m.group(0).split())
    expected = ' '.join(expected_sig.split())
    return actual == expected


def _has_finish_stop(source: str) -> bool:
    """Check for $finish or $stop outside comments."""
    stripped = _strip_sv_comments(source)
    return bool(re.search(r'\$(?:finish|stop)\b', stripped))


def _has_synthesis_off(source: str) -> bool:
    """Check for synthesis translate_off directive."""
    return bool(re.search(r'synthesis\s+translate_off', source, re.IGNORECASE))


def _check_assertion_identity(source: str, property_names: list) -> list:
    """Soft check: named assertions whose body is a known tautology.
    Returns list of (name, body) pairs that are suspicious. Warn-only."""
    suspicious = []
    tautology_bodies = {'1', "1'b1", '|0', '~0', "1'b1"}
    for name in property_names:
        # Look for: <name>: assert property (<body>)
        m = re.search(
            re.escape(name) + r'\s*:\s*assert\s+property\s*\(\s*([^)]+?)\s*\)',
            source
        )
        if m:
            body = m.group(1).strip()
            if body in tautology_bodies:
                suspicious.append((name, body))
    return suspicious


def _has_assume_restrict(source: str, is_smv: bool = False) -> bool:
    """Check for assume/restrict injections that produce vacuous proofs.

    SV: assume property (...) or restrict property (...) over-constrain the
        model so EBMC proves assertions vacuously.
    SMV: INVAR, TRANS, FAIRNESS keywords add constraints not present in the
         original task file, narrowing the reachable state space.
    """
    if is_smv:
        stripped = _strip_smv_comments(source)
        if re.search(r'^\s*(?:INVAR|TRANS|FAIRNESS)\b', stripped, re.MULTILINE):
            return True
        return False
    else:
        stripped = _strip_sv_comments(source)
        if re.search(r'\bassume\s+(?:property\s*)?\(', stripped):
            return True
        if re.search(r'\brestrict\s+(?:property\s*)?\(', stripped):
            return True
        return False


def _compute_assertion_hash(source: str, is_smv: bool = False) -> str:
    """SHA256 of all assertion/property lines (stripped, in file order).

    Detects any modification to assertion bodies — weakening, rewriting,
    or swapping to match buggy behavior.
    """
    if is_smv:
        stripped = _strip_smv_comments(source)
        lines = [
            line.strip()
            for line in stripped.splitlines()
            if re.search(r'\b(?:LTLSPEC|CTLSPEC|INVARSPEC)\b', line)
        ]
    else:
        stripped = _strip_sv_comments(source)
        lines = [
            line.strip()
            for line in stripped.splitlines()
            if re.search(r'\bassert\s+(?:property|final)\b', line)
        ]
    combined = '\n'.join(lines)
    return hashlib.sha256(combined.encode()).hexdigest()


# ── EBMC invocation ──────────────────────────────────────────────────

def _run_ebmc(sv_file: str, top_module: str, bound: int,
              timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run EBMC and return dict with proved/refuted counts and raw output.

    Returns:
        {
          "exit_code": int,
          "proved": int,
          "refuted": int,
          "timed_out": bool,
          "stdout": str,
          "stderr": str,
        }
    """
    cmd = ["ebmc", sv_file, "--bound", str(bound)]
    if top_module:
        cmd += ["--module", top_module]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "proved": 0,
            "refuted": 0,
            "timed_out": True,
            "stdout": "",
            "stderr": f"EBMC timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {
            "exit_code": -1,
            "proved": 0,
            "refuted": 0,
            "timed_out": False,
            "stdout": "",
            "stderr": "ebmc binary not found",
        }

    # Parse PROVED / REFUTED from stdout
    proved = len(re.findall(r':\s*PROVED\b', stdout, re.IGNORECASE))
    refuted = len(re.findall(r':\s*(?:REFUTED|FAILED)\b', stdout, re.IGNORECASE))

    return {
        "exit_code": exit_code,
        "proved": proved,
        "refuted": refuted,
        "timed_out": timed_out,
        "stdout": stdout[:2000],
        "stderr": stderr[:500],
    }


# ── Main entry point ─────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print("Usage: python scoring.py <config_path> <output_path>", file=sys.stderr)
        sys.exit(1)

    config_path = sys.argv[1]
    output_path = sys.argv[2]

    config = json.loads(Path(config_path).read_text())
    sv_file = config["sv_file"]
    top_module = config.get("top_module", "")
    bound = config.get("bound", 10)
    timeout = config.get("timeout_seconds", DEFAULT_TIMEOUT)
    num_expected = config.get("num_expected_properties", 1)
    property_names = config.get("property_names", [])
    module_signature = config.get("module_signature", "")
    is_smv = sv_file.endswith(".smv")

    scoring_cfg = config.get("scoring", {})
    center = scoring_cfg.get("sigmoid_center", SIGMOID_CENTER)
    scale = scoring_cfg.get("sigmoid_scale", SIGMOID_SCALE)

    metadata = {
        "sv_file": sv_file,
        "top_module": top_module,
        "bound": bound,
        "num_expected_properties": num_expected,
    }

    # --- Read student file ---
    sv_path = Path(sv_file)
    if not sv_path.exists():
        metadata["error"] = "student file not found"
        _write_result(output_path, 0.0, metadata)
        return

    source = sv_path.read_text()
    if not source.strip():
        metadata["error"] = "student file is empty"
        _write_result(output_path, 0.0, metadata)
        return

    # ── ANTI-CHEAT 1: Property count ────────────────────────────────
    actual_count = _count_assert_lines(source, is_smv=is_smv)
    metadata["property_count_actual"] = actual_count
    metadata["property_count_expected"] = num_expected
    if actual_count < num_expected:
        metadata["cheat"] = "property_deletion"
        metadata["error"] = f"Too few assertions: found {actual_count}, expected {num_expected}"
        _write_result(output_path, 0.0, metadata)
        return

    # ── ANTI-CHEAT 2: Property names ────────────────────────────────
    if property_names:
        missing = _check_property_names(source, property_names, is_smv=is_smv)
        metadata["property_names_missing"] = missing
        if missing:
            metadata["cheat"] = "property_renaming"
            metadata["error"] = f"Named assertions missing: {missing}"
            _write_result(output_path, 0.0, metadata)
            return

    # ── ANTI-CHEAT 3: Trivial assertions ────────────────────────────
    if _has_trivial_assertion(source, is_smv=is_smv):
        metadata["cheat"] = "trivial_assertion"
        metadata["error"] = "Tautological assertion detected (assert property(1'b1) or equivalent)"
        _write_result(output_path, 0.0, metadata)
        return

    # ── ANTI-CHEAT 4: Module interface ──────────────────────────────
    if module_signature and not is_smv:
        if not _check_module_signature(source, module_signature):
            metadata["cheat"] = "module_signature_changed"
            metadata["error"] = f"Module signature changed from expected: {module_signature}"
            _write_result(output_path, 0.0, metadata)
            return

    # ── ANTI-CHEAT 5: $finish / $stop ───────────────────────────────
    if not is_smv and _has_finish_stop(source):
        metadata["cheat"] = "finish_stop"
        metadata["error"] = "$finish or $stop found — would halt EBMC early"
        _write_result(output_path, 0.0, metadata)
        return

    # ── ANTI-CHEAT 6: synthesis translate_off ───────────────────────
    if not is_smv and _has_synthesis_off(source):
        metadata["cheat"] = "synthesis_off"
        metadata["error"] = "// synthesis translate_off found — would hide assertions"
        _write_result(output_path, 0.0, metadata)
        return

    # ── ANTI-CHEAT 8: assume / restrict / INVAR injection ───────────
    # Some tasks include environment-constraint assumes (e.g. AXI valid-hold).
    # Config may set "expected_assume_count" to whitelist them.
    expected_assumes = config.get("expected_assume_count", 0)
    if _has_assume_restrict(source, is_smv=is_smv):
        # Count actual assume property statements
        if is_smv:
            actual_assumes = len(re.findall(
                r'^\s*(?:INVAR|TRANS|FAIRNESS)\b',
                _strip_smv_comments(source), re.MULTILINE))
        else:
            actual_assumes = len(re.findall(
                r'\bassume\s+(?:property\s*)?\(',
                _strip_sv_comments(source)))
        if actual_assumes > expected_assumes:
            metadata["cheat"] = "assume_inject"
            metadata["error"] = (
                f"assume/restrict injection: found {actual_assumes} "
                f"assume(s), expected at most {expected_assumes}"
            )
            _write_result(output_path, 0.0, metadata)
            return

    # ── ANTI-CHEAT 9: Assertion body integrity ───────────────────────
    expected_hash = config.get("assertion_body_hash", "")
    if expected_hash:
        actual_hash = _compute_assertion_hash(source, is_smv=is_smv)
        metadata["assertion_body_hash_actual"] = actual_hash
        if actual_hash != expected_hash:
            metadata["cheat"] = "assertion_body_modified"
            metadata["error"] = "Assertion bodies have been modified from the original"
            _write_result(output_path, 0.0, metadata)
            return

    # ── ANTI-CHEAT 7: Assertion identity (warn-only, soft) ──────────
    if property_names and not is_smv:
        suspicious = _check_assertion_identity(source, property_names)
        if suspicious:
            metadata["assertion_identity_warning"] = [
                {"name": n, "body": b} for n, b in suspicious
            ]

    # ── WARMUP: warm ebmc before real invocation ─────────────────────
    try:
        subprocess.run(["ebmc", "--version"], capture_output=True, timeout=5)
    except Exception:
        pass

    # ── Run EBMC ─────────────────────────────────────────────────────
    t_start = time.monotonic()
    ebmc_result = _run_ebmc(sv_file, top_module, bound, timeout=timeout)
    t_elapsed = time.monotonic() - t_start

    metadata["ebmc_exit_code"] = ebmc_result["exit_code"]
    metadata["ebmc_proved"] = ebmc_result["proved"]
    metadata["ebmc_refuted"] = ebmc_result["refuted"]
    metadata["ebmc_timed_out"] = ebmc_result["timed_out"]
    metadata["ebmc_elapsed_seconds"] = round(t_elapsed, 3)
    metadata["ebmc_stdout"] = ebmc_result["stdout"]

    if ebmc_result["timed_out"]:
        # Treat timed-out properties as refuted — graceful degradation
        metadata["error"] = f"EBMC timed out after {timeout}s"
        proved = ebmc_result["proved"]  # partial credit for proved ones
    else:
        proved = ebmc_result["proved"]

    # Use max(proved, 0) as numerator; denominator is num_expected
    proved_fraction = min(1.0, proved / max(num_expected, 1))
    metadata["proved_fraction"] = round(proved_fraction, 4)

    score = compute_score(proved_fraction, center=center, scale=scale)
    _write_result(output_path, score, metadata)


def _write_result(output_path: str, score: float, metadata: dict):
    Path(output_path).write_text(
        json.dumps({"score": round(score, 6), "metadata": metadata}, indent=2)
    )


if __name__ == "__main__":
    main()
