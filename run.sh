#!/bin/bash
# Build and run this environment.
#
# Usage:
#   ./run.sh build          Build the container image
#   ./run.sh test <task>    Run scoring on a specific task
#   ./run.sh shell          Open a shell inside the container
#   ./run.sh list           List available tasks

set -euo pipefail

IMAGE_NAME="$(basename "$(pwd)" | tr '_' '-' | tr ' ' '-' | tr '[:upper:]' '[:lower:]')"

case "${1:-help}" in
  build)
    echo "Building $IMAGE_NAME..."
    docker build -t "$IMAGE_NAME" -f Containerfile .
    echo "Done. Run './run.sh list' to see tasks."
    ;;
  test)
    TASK="${2:?Usage: ./run.sh test <task-id>}"
    echo "Testing task: $TASK"
    docker run --rm --user root "$IMAGE_NAME" bash -c "
      /root/.venv/bin/python /root_data/eval/scoring.py /root_data/eval/configs/${TASK}.json /tmp/score.json &&
      cat /tmp/score.json | python -m json.tool
    "
    ;;
  shell)
    echo "Opening shell as student user..."
    docker run --rm -it "$IMAGE_NAME" bash
    ;;
  list)
    echo "Available tasks:"
    docker run --rm --user root "$IMAGE_NAME" bash -c "ls /root_data/eval/configs/*.json 2>/dev/null | xargs -I{} basename {} .json | sort"
    ;;
  dryrun)
    echo "Running dry-run tests..."
    echo "Build the image first for accurate scoring: ./run.sh build"
    echo ""
    python3 dryrun.py . "${@:2}"
    ;;
  help|*)
    echo "Usage: ./run.sh <command>"
    echo ""
    echo "Commands:"
    echo "  build          Build the container image"
    echo "  test <task>    Run scoring on a specific task"
    echo "  shell          Open a shell inside the container"
    echo "  list           List available tasks"
    echo "  dryrun         Run automated tests (scores via Docker)"
    ;;
esac
