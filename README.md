# Formal Hardware Verification

An RL training environment for formal hardware verification using EBMC (hw-cbmc). 40 tasks across SystemVerilog circuit debugging, NuSMV model fixing, and protocol FSM implementation, calibrated so frontier models score 0.0-1.0 with meaningful variance.

**What this trains:** An agent that can read a buggy hardware description, understand formal properties, trace multi-cycle counterexamples from EBMC, identify wiring/routing/timing bugs in complex pipelines, and write correct fixes. The agent must reason about non-blocking assignment semantics, pipeline forwarding, feedback loops, and protocol handshakes.

## Why Formal Hardware Verification?

EBMC is a bounded model checker: it exhaustively explores all reachable states up to a given bound and mathematically proves or refutes properties. A property either **PROVES** (holds for all inputs across all time steps) or is **REFUTED** (a concrete counterexample is found). This makes correctness guarantees far stronger than simulation tests.

The hard tasks require debugging circuits with **3-4 interacting wiring bugs** in feedback paths. Fixing one bug changes the symptoms of the others, forcing iterative debugging: run EBMC, read counterexample, fix one bug, re-run, discover new failure, repeat.

## Tasks

40 tasks in 3 difficulty tiers.

### Hard (10 tasks) -- Complex microarchitectural circuits with interacting bugs

| Task | Circuit | Bugs | Properties | Bound |
|------|---------|------|------------|-------|
| **fix-scoreboard-bypass** | Pipeline with RAW hazard bypass | 4 (condition/mux/operand/dest) | 8 | 10 |
| **fix-cache-ctrl** | Direct-mapped write-back cache | 3 (writeback index/fill source/read output) | 7 | 8 |
| **fix-branch-pred** | 2-bit saturating counter predictor | 3 (table index/threshold/update direction) | 7 | 10 |
| **fix-dma-engine** | 2-channel DMA with round-robin | 3 (address source/turn flip/completion check) | 7 | 12 |
| **fix-regfile-fwd** | Dual-read regfile with write forwarding | 3 (forward condition/RMW operation/read routing) | 7 | 8 |
| **fix-hazard-ctrl** | 3-stage pipeline hazard detector | 3 (hazard compare/stall signal/forward mux) | 7 | 10 |
| **fix-arb-lock** | Bus arbiter with lock/burst/priority | 3 (burst load/burst decrement/lock acquisition) | 7 | 10 |
| **fix-fifo-async** | Async FIFO with Gray-code pointers | 3 (Gray encode/full detect/sync stages) | 7 | 10 |
| **fix-timer-irq** | Dual-compare timer with prescaler | 3 (mask polarity/compare source/compare target) | 7 | 15 |
| **fix-mem-ctrl** | Memory controller with bank interleaving | 3 (bank select/pending track/response mux) | 7 | 10 |

### Medium (9 tasks) -- Protocol FSMs and iterative algorithms

| Task | Type | Properties | Description |
|------|------|------------|-------------|
| fix-pipeline-alu | fix | 5 | 2-stage ALU pipeline with swapped latch targets and wrong opcode source |
| fix-restoring-div | fix | 5 | 8-bit restoring division with wrong shift direction and off-by-one step |
| fix-fifo-ptrs | fix | 7 | 8-entry FIFO with wrong write address and pointer routing |
| fix-fifo-credit | fix | 7 | Credit-based FIFO with wrong register updates |
| fix-pipeline-mac | fix | 6 | 3-stage MAC pipeline with wrong operand and clear routing |
| fix-uart-rx | fix | 6 | UART 4N1 receiver with wrong data source and assembly |
| fix-i2c-ctrl | fix | 6 | I2C master with wrong bit index and ACK signal source |
| fix-booth-mul | fix | 6 | Booth radix-2 multiplier with wrong shift tap and commit timing |
| implement-axi-handshake | implement | 6 | AXI-lite write FSM from scratch with assume constraints |

### Easy (21 tasks) -- Single-bug circuits and simple FSMs

Combinational (bound=1): fix-decoder, fix-mux-select, fix-adder-carry, fix-priority-enc, fix-hamming, fix-barrel-shift

Sequential (bound=10-20): fix-counter-reset, fix-counter-wrap, fix-shift-dir, fix-dff-enable, fix-fibonacci, fix-lfsr, fix-gray-counter, fix-watchdog, fix-crc8, fix-spi-slave, fix-ring-buffer, fix-traffic-light, fix-arbiter-fair, implement-arb3

NuSMV (bound=10-20): fix-smv-counter, fix-smv-onehot, fix-smv-ring3, fix-smv-mod8

## Scoring

Every task produces a float in [0, 1] from a deterministic oracle. No LLM-as-judge.

**Formula:** `sigmoid(scale * (proved_fraction - center))`

| Component | Description |
|-----------|-------------|
| **proved_fraction** | Properties proved / total properties [0, 1] |
| **sigmoid_center** | Per-task calibration (0.55-0.95) |
| **sigmoid_scale** | Per-task steepness (8-20) |

**Anti-cheat layers:**
- Assertion body hash -- SHA256 of all `assert property` lines; any modification scores 0
- Module signature check -- port list must match config
- Assume/restrict injection detection (with whitelist for environmental constraints)
- Synthesis translate_off detection
- Property count verification

## Hints

Hard tasks include optional `// HINT:` comments near the most subtle bugs. These can be stripped for harder evaluation or preserved for guided training.

## Student Tools

The student agent operates in a sandboxed bash environment with three tools:

| Tool | What it does |
|------|-------------|
| `bash` | Run shell commands, read files, run `ebmc`, check output |
| `view_lines_in_file` | Read specific line ranges from a file |
| `replace_in_file` | Edit a file by replacing an exact string match |

The student can read `/workdir/data/` (workspace) and `/workdir/shared/` (reference). It cannot read `/root_data/` (scoring, configs).

Typical workflow:
1. Read the task file in `/workdir/data/`
2. Run `ebmc <file> --bound <N>` to see which properties fail
3. Read the counterexample trace to identify the bug
4. Edit using `replace_in_file`
5. Re-run ebmc -- iterate until all properties PROVE

## Setup

Requires Docker/Podman. No GPU or special hardware.

```bash
podman build -t hw-cbmc-demo .
```

## Running Evaluations

```bash
# Build the container
podman build -t hw-cbmc-demo .

# Run evaluation on all tasks
python3 dryrun.py . --all-tasks --model <model> --output <model>_run1.json

# Update scorecard
./update_results.sh
```

## Security Model

| Path | Access | Contents |
|------|--------|----------|
| `/root_data/` | Root only (0700) | Scoring scripts, eval configs |
| `/workdir/shared/` | Read-only | Reference material (SVA syntax, NuSMV guide) |
| `/workdir/data/` | Read/write | Student workspace (one file per task) |

Production: `read_only: true`, `network_mode: none`, `cap_drop: ALL`, `no-new-privileges`.

## Baseline Results

![Performance heatmap](scores.svg)
