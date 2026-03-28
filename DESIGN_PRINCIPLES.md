# hw-cbmc-demo Design Principles

## Scoring: proof-based, not time-based

Score is determined entirely by `proved_fraction = num_proved / num_expected_properties`.
Time is recorded in metadata but does NOT affect the reward. This eliminates hardware speed
as a confound entirely -- a correct fix scores the same on a slow VM as on a fast workstation.

## Anti-cheat: seven checks before EBMC

All seven anti-cheat checks run BEFORE the EBMC invocation. This prevents:

1. **Property deletion**: count `assert property`/`assert final` lines. If fewer than expected → score 0.
2. **Property renaming**: each named label (`p_reset:`, `p_inc:`) must still appear. If missing → score 0.
3. **Trivial assertions**: `assert property(1'b1)` or `assert final(1)` always prove. If found → score 0.
4. **Module interface change**: the top-level `module name(port list)` must match the reference. If changed → score 0.
5. **Simulation halting**: `$finish` or `$stop` would end EBMC's simulation early. If found → score 0.
6. **Synthesis directives**: `// synthesis translate_off` hides assertions from tools. If found → score 0.
7. **Assertion identity** (soft/warn): named assertions whose body is `(1)` or `(1'b1)` -- warns but does not hard-block (noisy to block; caught by property count if removed).

## Warmup: eliminate cold-start spike

EBMC's first call after container start has a ~0.5s cold-start due to dynamic linker cache.
Two warmup mitigations:
- Containerfile runs `ebmc --version` in the final layer (warms disk cache at build time)
- `scoring.py` runs `ebmc --version` before the real invocation (warms at runtime)

## Per-task workspace isolation

Each task episode copies ONLY the target `.sv`/`.smv` file to the student's workspace.
This prevents agents from accidentally editing the wrong circuit file.

The evaluation runner extracts `sv_filename` from each task's `__init__.py`
and copies only that file to the temp workdir.

## Timeout: graceful degradation

Each task config has a `timeout_seconds` field. If EBMC times out:
- Properties proved before timeout count toward the score
- Timed-out properties are treated as REFUTED (score degrades gracefully)
- No crash -- the scoring script returns a valid JSON with partial credit

Default timeouts by tier:
- Tier 1 (combinational, bound=1): 5s
- Tier 2 (sequential, bound=10-15): 30s
- Tier 3 (FSM, bound=15-20): 60s
- Tier 4 (NuSMV): 30s

## Scoring calibration

Sigmoid curve: `sigmoid(8.0 * (proved_fraction - 0.55))`

| proved_fraction | score |
|----------------|-------|
| 0.0 | ~0.03 |
| 0.5 | ~0.35 |
| 0.55 | ~0.50 |
| 1.0 | ~0.97 |

This gives the agent a gradient signal at all levels -- not just binary pass/fail.
A correct fix scores ~0.97 (not 1.0) to preserve signal at the top.

## Security model

| Path | Access | Contents |
|------|--------|----------|
| `/root_data/` | Root only (0700) | scoring.py, task configs |
| `/workdir/shared/` | Read-only (444) | sv_reference.md |
| `/workdir/data/` | Student read/write | circuit files |

Production: `read_only: true`, `network_mode: none`, `cap_drop: ALL`, `no-new-privileges`.
