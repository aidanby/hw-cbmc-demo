# Formal Hardware Verification

A Reinforcement Learning training environment for formal hardware verification using EBMC (hw-cbmc). It contains 12 tasks across two domains: SystemVerilog circuit debugging and NuSMV finite state machine debugging.

**What this trains:** An agent that can read a buggy hardware description, understand the formal properties it must satisfy, identify the logic error, and write the correct fix so all EBMC properties are proved. The agent must reason about clocks, state machines, carry propagation, and temporal logic — not just pass tests.

## Overview: What is Formal Hardware Verification?

EBMC (the hw-cbmc tool) is a bounded model checker for hardware designs. Unlike simulation-based testing, it exhaustively explores all reachable states up to a given bound and mathematically proves or refutes properties. A property either **PROVES** (holds for all inputs across all time steps up to the bound) or is **REFUTED** (a concrete counterexample is found). This makes correctness guarantees far stronger than unit tests.

The environment uses two hardware description languages:
- **SystemVerilog** — synthesizable digital circuit descriptions (counters, FSMs, arithmetic units, shift registers, arbiters)
- **NuSMV** — symbolic model files for finite state machines with LTL specifications

### Environment Workflow

A single training episode follows this structure:

1. **The Task:** The student model receives a task prompt describing a buggy hardware module — a counter with wrong reset polarity, a shift register shifting the wrong direction, an FSM stuck in a state. The student receives the buggy `.sv` or `.smv` file in `/workdir/data/`.
2. **The Outcome:** The student operates in a sandboxed bash environment. It reads the file, identifies the logic error, writes the fix, and iteratively tests using `ebmc`. The final artifact is the corrected hardware description file.
3. **The Verification Mechanism:** The environment relies on formal model checking, not LLM-as-a-judge.
   - The student's final code is passed to EBMC, which runs SAT-based bounded model checking.
   - Each named property is either PROVED (holds for all traces up to the bound) or REFUTED (a counterexample exists).
   - Score is determined by the fraction of properties proved — the agent must fix the actual logic bug, not just make tests pass.

### The Scoring Signal

The EBMC results are translated into a dense reward signal for Reinforcement Learning:

* **Property Fraction Gate:** Score = sigmoid(scale × (proved_fraction − center)), calibrated so a fully fixed circuit scores ~1.0 and a fully broken one scores ~0.03.
* **Anti-Cheat — Property Integrity:** 9 checks run before EBMC. Deleting assertions, injecting `assume property` to produce vacuous proofs, adding `INVAR`/`TRANS` constraints in NuSMV, or modifying assertion bodies all score 0.
* **Anti-Cheat — Assertion Body Hash:** SHA-256 of all assertion lines is stored per task. Any rewrite of property bodies — weakening, swapping, or replacing with tautologies — is detected and scores 0.
* **Final Score:** A continuous scalar in [0, 1] determined by proved fraction through a calibrated sigmoid. Most tasks use center=0.55; tasks where some properties hold on the buggy code use center=0.75 to ensure a meaningful gradient.
* **Efficiency:** Scoring is based on property correctness only — tool call count does not affect the score.

## Student Tools

The student agent operates in a sandboxed bash environment with three tools:

| Tool | What it does |
|------|-------------|
| `bash` | Run shell commands. Read files, run EBMC, check output. |
| `view_lines_in_file` | Read specific line ranges from a file. |
| `replace_in_file` | Edit a file by replacing an exact string match. |

The student can read `/workdir/data/` (workspace) and `/workdir/shared/` (reference). It cannot read `/root_data/` (scoring, configs).

Typical workflow:

1. `bash: cat /workdir/data/FixCounterReset.sv` — read the buggy file
2. `bash: ebmc /workdir/data/FixCounterReset.sv --bound 10` — see which properties are REFUTED and read the counterexample
3. `replace_in_file` — fix the logic error
4. `bash: ebmc /workdir/data/FixCounterReset.sv --bound 10` — verify all properties PROVED
5. Repeat until exit code 0 (all PROVED)

## Task List

| Task | Description | Language | Properties |
|------|-------------|----------|-----------|
| fix-counter-reset | Reset polarity inverted (`!reset` instead of `reset`) | SV | 2 |
| fix-counter-wrap | BCD counter wraps at 15 instead of 9 | SV | 3 |
| fix-adder-carry | Carry lookahead uses `&` instead of `\|` | SV | 2 |
| fix-ring-buffer | Count increments on read instead of decrement | SV | 3 |
| fix-shift-dir | Shift register shifts left instead of right | SV | 2 |
| fix-mux-select | Select bits indexed in wrong order | SV | 2 |
| fix-decoder | 2-to-4 decoder missing case for `2'b11` | SV | 3 |
| fix-dff-enable | D flip-flop ignores enable signal | SV | 2 |
| fix-arbiter-fair | Round-robin arbiter always grants client 0 | SV | 3 |
| fix-traffic-light | Traffic light FSM stuck in YELLOW state | SV | 3 |
| fix-smv-counter | NuSMV counter increments by 2 instead of 1 | NuSMV | 2 |
| fix-smv-onehot | NuSMV one-hot FSM: wrong next-state for s1 | NuSMV | 3 |

## Setup

Requires Docker or Podman. No GPU or special hardware.

```bash
cd hw-cbmc-demo
podman build -f Containerfile -t hw-cbmc-demo .   # build the scoring container
```

## RL Training Integration

### Docker / Podman

```bash
./rl_wrapper.sh . <task_id> /tmp/student_workspace
# Returns JSON: {"score": 0.73, "metadata": {...}}
```

### Kubernetes

Drop all egress from scoring pods via `NetworkPolicy`.

```bash
kubectl apply -f k8s-rl-job.yaml
kubectl logs job/rl-episode
```

## Security Model

| Path | Access | Contents |
|------|--------|----------|
| `/root_data/` | Root only (0700) | Scoring scripts, eval configs, assertion hashes |
| `/workdir/shared/` | Read-only | Reference material |
| `/workdir/data/` | Read/write | Student workspace (buggy files) |

Production: `read_only: true`, `network_mode: none`, `cap_drop: ALL`, `no-new-privileges`.

## Scoring Reproducibility

Scores are fully deterministic. EBMC is a SAT-based model checker with no randomness — the same circuit produces identical PROVED/REFUTED outcomes on every run. Verified: running the same student submission 10 times produces identical scores (stdev = 0.0).

## Baseline Results

All 12 tasks validated against oracle fixes:

| Condition | Score Range |
|-----------|-------------|
| Buggy file (no fix) | 0.01 – 0.41 |
| Oracle fix applied | 1.0 (all tasks) |
