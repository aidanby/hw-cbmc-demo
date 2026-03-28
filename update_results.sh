#!/bin/bash
# update_results.sh - Regenerate README heatmap from run result files.
#
# Call this after adding or updating {model}_run{N}.json files.
# Auto-discovers all run files, computes stats, generates SVG heatmap.
#
# Usage:
#   ./update_results.sh                    # if finalize_readme.py is in PATH or parent directory
#   ./update_results.sh /path/to/finalize_readme.py

set -euo pipefail

ENV_DIR="$(cd "$(dirname "$0")" && pwd)"

# Find finalize_readme.py
FINALIZE=""
if [ $# -ge 1 ] && [ -f "$1" ]; then
    FINALIZE="$1"
elif [ -f "$ENV_DIR/finalize_readme.py" ]; then
    FINALIZE="$ENV_DIR/finalize_readme.py"
elif [ -f "$ENV_DIR/../finalize_readme.py" ]; then
    FINALIZE="$ENV_DIR/../finalize_readme.py"
elif command -v finalize_readme.py &>/dev/null; then
    FINALIZE="finalize_readme.py"
fi

if [ -z "$FINALIZE" ]; then
    echo "ERROR: Cannot find finalize_readme.py"
    echo "Usage: ./update_results.sh /path/to/finalize_readme.py"
    exit 1
fi

# Restore any .bak files that were overwritten with bad data
for bak in "$ENV_DIR"/*_run*.json.bak; do
    [ -f "$bak" ] || continue
    original="${bak%.bak}"
    if [ -f "$original" ]; then
        # Check if original was corrupted (all scores = 0)
        all_zero=$(python3 -c "
import json, sys
d = json.load(open('$original'))
scores = [r.get('score', 0) for r in d.get('results', [])]
print('yes' if all(s == 0 for s in scores) and len(scores) > 0 else 'no')
" 2>/dev/null || echo "no")
        if [ "$all_zero" = "yes" ]; then
            echo "Restoring $original from backup (was overwritten with zeros)"
            cp "$bak" "$original"
        fi
    fi
done

# Count run files
RUN_COUNT=$(ls "$ENV_DIR"/*_run*.json 2>/dev/null | grep -v '.bak' | wc -l)
echo "Found $RUN_COUNT run files"

if [ "$RUN_COUNT" -eq 0 ]; then
    echo "No run files found. Run evaluations first with ./run_eval.sh"
    exit 1
fi

# Regenerate
python3 "$FINALIZE" "$ENV_DIR"
echo ""
echo "Done. Commit with:"
echo "  git add scores.svg README.md && git commit -m 'docs: update results' && git push"
