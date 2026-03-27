#!/bin/bash
# ==============================================================================
# RL Task Wrapper Script
# ==============================================================================
# A reference script for executing a single Reinforcement Learning episode.
# It mounts a student submission directory into the environment's isolated 
# Docker container and retrieves the resulting JSON score.
#
# Usage: ./rl_wrapper.sh <environment_path> <task_id> <student_submission_dir>
# Example: ./rl_wrapper.sh lean-theorem-proving fix-induction-step /tmp/workdir
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <environment_path> <task_id> <student_submission_dir>"
    echo "Example: $0 lean-theorem-proving fix-induction-step /tmp/workdir"
    exit 1
fi

ENV_DIR=$(realpath "$1")
TASK_ID="$2"
STUDENT_DIR=$(realpath "$3")

# Validate environment
if [ ! -d "$ENV_DIR" ]; then
    echo "Error: Environment directory '$ENV_DIR' does not exist."
    exit 1
fi

# The Docker image name is conventionally derived from the environment directory name
IMAGE_NAME=$(basename "$ENV_DIR" | tr '_' '-' | tr ' ' '-' | tr '[:upper:]' '[:lower:]')

# Ensure the student directory has the necessary structure before mounting
if [ ! -d "$STUDENT_DIR" ]; then
    echo "Error: Student submission directory '$STUDENT_DIR' does not exist."
    exit 1
fi

# ============================================================
# Execute the Scoring Container
# ============================================================
# The container mounts the student submission to /workdir/data
# and the read-only shared reference data to /workdir/shared.
# It invokes the internal scoring script on the specific task config.

# The result JSON is piped out of the container so the RL loop can parse it.
docker run --rm \
    --user root \
    --network none \
    -v "${STUDENT_DIR}:/workdir/data:rw" \
    -v "${ENV_DIR}/shared_data:/workdir/shared:ro" \
    "$IMAGE_NAME" \
    bash -c "
        /root/.venv/bin/python /root_data/eval/scoring.py '/root_data/eval/configs/${TASK_ID}.json' /tmp/score.json > /dev/null 2>&1
        cat /tmp/score.json 2>/dev/null || echo '{\"score\": 0.0, \"error\": \"Scoring script failed to output JSON\"}'
    "
