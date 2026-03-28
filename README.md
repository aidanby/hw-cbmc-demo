# Formal Hardware Verification

A Reinforcement Learning training environment for formal hardware verification using EBMC (hw-cbmc). It contains 21 tasks across two domains: SystemVerilog circuit debugging and NuSMV finite state machine debugging.

**What this trains:** An agent that can read a buggy hardware description, understand the formal properties it must satisfy, identify the logic error, and write the correct fix so all EBMC properties are proved. The agent must reason about clocks, state machines, carry propagation, and temporal logic — not just pass tests.

## Overview: What is Formal Hardware Verification?

EBMC (the hw-cbmc tool) is a bounded model checker for hardware designs. Unlike simulation-based testing, it exhaustively explores all reachable states up to a given bound and mathematically proves or refutes properties. A property either **PROVES** (holds for all inputs across all time steps up to the bound) or is **REFUTED** (a concrete counterexample is found). This makes correctness guarantees far stronger than unit tests.

The environment uses two hardware description languages:
- **SystemVerilog** — synthesizable digital circuit descriptions (counters, FSMs, arithmetic units, shift registers, arbiters, encoders, LFSRs)
- **NuSMV** — symbolic model files for finite state machines with LTL specifications

### Environment Workflow

A single training episode follows this structure:

1. **The Task:** The student model receives a task prompt describing a buggy hardware module. The student receives the buggy `.sv` or `.smv` file in `/workdir/data/`.
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

## Task List

**Tier 1 — Combinational (bound=1)**

| Task | Description | Properties | Bugs |
|------|-------------|-----------|------|
| fix-adder-carry | 4-bit carry-lookahead adder: wrong generate operators and carry input | 3 | 3 |
| fix-decoder | 2-to-4 decoder: wrong outputs for 3 cases | 5 | 3 |
| fix-mux-select | 4-to-1 mux: wrong data assignments in 3 cases | 4 | 3 |
| fix-priority-enc | 4-to-2 priority encoder: wrong output indices for 3 cases | 4 | 3 |
| fix-hamming | Hamming(7,4) encoder: all 3 parity equations cover wrong bit positions | 3 | 3 |
| fix-barrel-shift | 8-bit logical right barrel shifter: zero output for sel=0, arithmetic shift for sel=1, cases 4/7 swapped | 4 | 4 |

**Tier 2 — Simple Sequential (bound=10–20)**

| Task | Description | Properties | Bugs |
|------|-------------|-----------|------|
| fix-counter-reset | 8-bit counter: reset polarity inverted, increments by 2 | 3 | 2 |
| fix-counter-wrap | BCD counter: threshold off-by-one, wraps to 1 instead of 0 | 4 | 2 |
| fix-dff-enable | D flip-flop: wrong reset value, enable signal ignored | 4 | 2 |
| fix-shift-dir | 8-bit shift register: wrong initial value, wrong reset value, shifts left not right | 4 | 3 |
| fix-fibonacci | Fibonacci generator: wrong reset values, curr not incremented by prev | 4 | 3 |
| fix-crc8 | CRC-8/SMBUS serial register: reset to 0xFF instead of 0x00, polynomial 0x83 not 0x07 | 3 | 2 |
| fix-gray-counter | 4-bit Gray code counter: wrong reset output, step +2 not +1, shift >>2 not >>1 | 3 | 3 |
| fix-lfsr | 4-bit LFSR: zero initial seed, wrong reset seed, wrong feedback taps | 3 | 3 |

**Tier 3 — FSM / Multi-register (bound=15–20)**

| Task | Description | Properties | Bugs |
|------|-------------|-----------|------|
| fix-arbiter-fair | 2-client round-robin arbiter: wrong turn condition, both turn-update assignments inverted | 6 | 3 |
| fix-ring-buffer | 4-entry ring buffer: write pointer not incremented, count increments on read, wrong full threshold | 4 | 3 |
| fix-traffic-light | 4-state traffic light FSM: 3 wrong state transitions | 5 | 3 |

**Tier 4 — NuSMV (bound=10–20)**

| Task | Description | Properties | Bugs |
|------|-------------|-----------|------|
| fix-smv-counter | Counter over 0..15: wrong initial value, increments by 4 | 3 | 2 |
| fix-smv-onehot | One-hot FSM: wrong next-state for s1, wrong next-state for s2 | 3 | 2 |
| fix-smv-mod8 | Modulo-8 counter: wraps to 1 not 0, step +2 not +1 | 4 | 2 |
| fix-smv-ring3 | Token-ring mutual exclusion: p1→p0 instead of p1→p2 | 4 | 1 |

## Scorecard — 4 Models, 21 Tasks

Scores are the result of a single dryrun pass per model. Each task: student agent reads buggy file, edits, runs ebmc, submits. Score = sigmoid((proved/total) − center).

```
Task                     claude-sonnet-4-6    claude-haiku-4-5    gemini-2.5-flash    gemini-2.0-flash
─────────────────────────────────────────────────────────────────────────────────────────────────────
fix-adder-carry          1.000                1.000               1.000               0.385
fix-arbiter-fair         1.000                1.000               1.000               1.000
fix-barrel-shift         1.000                1.000               1.000               1.000
fix-counter-reset        1.000                1.000               1.000               1.000
fix-counter-wrap         1.000                1.000               1.000               1.000
fix-crc8                 1.000                1.000               1.000               1.000
fix-decoder              1.000                1.000               1.000               1.000
fix-dff-enable           1.000                1.000               1.000               1.000
fix-fibonacci            1.000                1.000               1.000               1.000
fix-gray-counter         1.000                1.000               1.000               1.000
fix-hamming              1.000                1.000               1.000               1.000
fix-lfsr                 1.000                0.737               0.737               1.000
fix-mux-select           1.000                1.000               1.000               1.000
fix-priority-enc         1.000                1.000               1.000               1.000
fix-ring-buffer          1.000                1.000               1.000               1.000
fix-shift-dir            1.000                1.000               1.000               1.000
fix-smv-counter          1.000                0.012               0.012               0.000
fix-smv-mod8             1.000                1.000               1.000               1.000
fix-smv-onehot           1.000                1.000               1.000               0.154
fix-smv-ring3            1.000                1.000               1.000               1.000
fix-traffic-light        1.000                1.000               1.000               1.000
─────────────────────────────────────────────────────────────────────────────────────────────────────
Average                  1.000                0.941               0.941               0.883
```

**Key discrimination patterns:**
- `fix-lfsr`: haiku and gemini-2.5 get 2/3 properties (fix seed bugs but can't identify correct maximal LFSR taps `q[3]^q[2]`).
- `fix-smv-counter`: haiku and gemini-2.5 can't figure out how to run ebmc on `.smv` files (score stays at floor). gemini-2.0 times out.
- `fix-smv-onehot`: gemini-2.0 partially fixes (1/3 properties).
- `fix-adder-carry`: gemini-2.0 fixes only 1/3 bugs (score 0.385).
- Sonnet-4-6 solves all 21 tasks correctly.

## Scoring Reproducibility

Scores are fully deterministic. EBMC is a SAT-based model checker with no randomness — the same circuit produces identical PROVED/REFUTED outcomes on every run.

## Student Tools

The student agent operates in a sandboxed bash environment with three tools:

| Tool | What it does |
|------|-------------|
| `bash` | Run shell commands. Read files, run `ebmc`, check output. |
| `view_lines_in_file` | Read specific line ranges from a file. |
| `replace_in_file` | Edit a file by replacing an exact string match. |

The student can read `/workdir/data/` (workspace) and `/workdir/shared/` (reference). It cannot read `/root_data/` (scoring, configs).

Typical workflow:
1. Read the task file in `/workdir/data/`
2. Run `ebmc <file> --top <module> --bound <N>` to see which properties fail
3. Edit using `replace_in_file`
4. Re-run ebmc to verify the fix

## Setup

Requires Docker/Podman. No GPU or special hardware.

```bash
podman build -t hw-cbmc-demo .
```

## RL Training Integration

### Docker

```bash
./rl_wrapper.sh . <task_id> /tmp/student_workspace
# Returns JSON: {"score": 0.73, "metadata": {...}}
```

### Kubernetes

```bash
kubectl apply -f k8s-rl-job.yaml
kubectl logs job/rl-episode
```

## Security Model

| Path | Access | Contents |
|------|--------|----------|
| `/root_data/` | Root only (0700) | Scoring scripts, eval configs |
| `/workdir/shared/` | Read-only | Reference material |
| `/workdir/data/` | Read/write | Student workspace |

Production: `read_only: true`, `network_mode: none`, `cap_drop: ALL`, `no-new-privileges`.
