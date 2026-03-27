#!/bin/bash
# run_eval.sh — Parallel evaluation runner for any environment.
#
# Maximizes throughput across available API keys without throttling.
# Supports 1 key (customer) or 2 keys (internal) modes.
#
# Usage:
#   ./run_eval.sh                          # 3 runs, auto-detect model
#   ./run_eval.sh --runs 5                 # 5 runs
#   ./run_eval.sh --model mistral/mistral-large-3 --runs 3
#   ./run_eval.sh --runs 3 --build         # build container first
#
# Concurrency math:
#   Each API key supports ~5 concurrent tasks (rate limit safe).
#   With 1 key:  1 process × 5 workers = 5 concurrent tasks
#   With 2 keys: 2 processes × 5 workers = 10 concurrent tasks
#   N runs are sequential per-key (each run evaluates all tasks in parallel).
#   Total wall time ≈ (N_runs / num_keys) × time_per_run
#
# Key detection priority:
#   1. LITELLM_API_KEY (always used if set — routes to any provider)
#   2. GEMINI_API_KEY (used as second parallel key, or primary if no LITELLM)
#   3. OPENAI_API_KEY / ANTHROPIC_API_KEY (fallback)

set -euo pipefail

# Defaults
NUM_RUNS=3
MODEL=""
MAX_WORKERS=5
BUILD=false

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --runs)     NUM_RUNS="$2"; shift 2 ;;
        --model)    MODEL="$2"; shift 2 ;;
        --workers)  MAX_WORKERS="$2"; shift 2 ;;
        --build)    BUILD=true; shift ;;
        *)          echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# Load .env if exists
[ -f .env ] && set -a && source .env && set +a

# Detect available keys
HAS_LITELLM=false
HAS_GEMINI=false
HAS_ANY=false

[ -n "${LITELLM_API_KEY:-}" ] && HAS_LITELLM=true && HAS_ANY=true
[ -n "${GEMINI_API_KEY:-}" ] && HAS_GEMINI=true && HAS_ANY=true
[ -n "${OPENAI_API_KEY:-}" ] && HAS_ANY=true
[ -n "${ANTHROPIC_API_KEY:-}" ] && HAS_ANY=true

if [ "$HAS_ANY" = false ]; then
    echo "ERROR: No API key found. Set one of:"
    echo "  export LITELLM_API_KEY=...     (routes to any provider via LiteLLM proxy)"
    echo "  export GEMINI_API_KEY=...      (Google AI directly)"
    echo "  export OPENAI_API_KEY=...      (OpenAI directly)"
    echo "  export ANTHROPIC_API_KEY=...   (Anthropic directly)"
    exit 1
fi

# Auto-detect model if not specified
if [ -z "$MODEL" ]; then
    if [ "$HAS_LITELLM" = true ]; then
        MODEL="gemini/gemini-2.5-flash"
    elif [ "$HAS_GEMINI" = true ]; then
        MODEL="gemini/gemini-2.5-flash"
    elif [ -n "${OPENAI_API_KEY:-}" ]; then
        MODEL="gpt-4o-mini"
    elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then
        MODEL="claude-haiku-4-5-20251001"
    fi
fi

# Determine parallel strategy
#   dual-key: split runs across 2 processes (LITELLM + GEMINI)
#   single-key: one process handles all runs
DUAL_KEY=false
if [ "$HAS_LITELLM" = true ] && [ "$HAS_GEMINI" = true ]; then
    # Only use dual-key if they're actually different keys
    if [ "${LITELLM_API_KEY:-}" != "${GEMINI_API_KEY:-}" ]; then
        DUAL_KEY=true
    fi
fi

# Count tasks for info display
TASK_COUNT=$(python3 -c "
import json, os
configs = [f for f in os.listdir('root_data/eval/configs') if f.endswith('.json')]
print(len(configs))
" 2>/dev/null || echo "?")

MODEL_SHORT=$(echo "$MODEL" | sed 's|.*/||')

echo "============================================================"
echo "EVALUATION: ${MODEL_SHORT}"
echo "============================================================"
echo "  Tasks:    ${TASK_COUNT}"
echo "  Runs:     ${NUM_RUNS}"
echo "  Workers:  ${MAX_WORKERS} per process"
if [ "$DUAL_KEY" = true ]; then
    echo "  Keys:     2 (LITELLM + GEMINI) — 2 parallel processes"
    echo "  Total concurrent: $((MAX_WORKERS * 2)) tasks"
else
    echo "  Keys:     1 — single process"
    echo "  Total concurrent: ${MAX_WORKERS} tasks"
fi
echo ""

# Build if requested
if [ "$BUILD" = true ]; then
    echo "[0] Building container..."
    ./run.sh build
    echo ""
fi

# Run function: executes N runs with a specific API key config
run_batch() {
    local KEY_VAR="$1"    # env var name containing the API key
    local KEY_VAL="$2"    # the actual key value
    local START_RUN="$3"  # first run number
    local END_RUN="$4"    # last run number
    local LABEL="$5"      # label for output files

    for i in $(seq "$START_RUN" "$END_RUN"); do
        local OUT_FILE="${MODEL_SHORT}_run${i}.json"
        echo "[${LABEL}] Run ${i}/${NUM_RUNS} → ${OUT_FILE}"
        LITELLM_API_KEY="$KEY_VAL" python3 dryrun.py . \
            --all-tasks \
            --model "$MODEL" \
            --max-workers "$MAX_WORKERS" \
            -o "$OUT_FILE" 2>&1 | sed "s/^/  [${LABEL}] /"
    done
}

if [ "$DUAL_KEY" = true ]; then
    # Split runs between two keys
    # Key A (LITELLM) gets runs 1..ceil(N/2)
    # Key B (GEMINI) gets runs ceil(N/2)+1..N
    SPLIT=$(( (NUM_RUNS + 1) / 2 ))

    echo "[dual-key] Splitting ${NUM_RUNS} runs: LITELLM handles 1-${SPLIT}, GEMINI handles $((SPLIT+1))-${NUM_RUNS}"
    echo ""

    # Launch both in parallel
    run_batch "LITELLM_API_KEY" "$LITELLM_API_KEY" 1 "$SPLIT" "LiteLLM" &
    PID_A=$!

    if [ "$NUM_RUNS" -gt "$SPLIT" ]; then
        run_batch "LITELLM_API_KEY" "$GEMINI_API_KEY" "$((SPLIT+1))" "$NUM_RUNS" "Gemini" &
        PID_B=$!
        wait $PID_A $PID_B
    else
        wait $PID_A
    fi
else
    # Single key: determine which key to use
    if [ "$HAS_LITELLM" = true ]; then
        KEY="$LITELLM_API_KEY"
    elif [ "$HAS_GEMINI" = true ]; then
        KEY="$GEMINI_API_KEY"
    elif [ -n "${OPENAI_API_KEY:-}" ]; then
        KEY="$OPENAI_API_KEY"
    elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then
        KEY="$ANTHROPIC_API_KEY"
    fi

    run_batch "LITELLM_API_KEY" "$KEY" 1 "$NUM_RUNS" "eval"
fi

echo ""
echo "============================================================"
echo "COMPLETE: ${NUM_RUNS} runs × ${TASK_COUNT} tasks"
echo "============================================================"
echo "Results: ${MODEL_SHORT}_run*.json"
echo ""
echo "Next steps:"
echo "  python3 finalize_readme.py .                    # update README with results"
echo "  python3 auto_calibrate.py .                     # check task difficulty"
