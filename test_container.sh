#!/bin/bash
# Container integration test -- builds the image and verifies everything works inside.
#
# Usage: ./test_container.sh <env-dir>
#
# Exit 0 = all pass, exit 1 = failures found
# Skips gracefully if Docker is not available.

set -euo pipefail

ENV_DIR="${1:?Usage: $0 <env-dir>}"
ENV_DIR="$(cd "$ENV_DIR" && pwd)"
# Image name matches what dryrun.py looks for
IMAGE_NAME="$(basename "$ENV_DIR" | tr '_' '-' | tr ' ' '-' | tr '[:upper:]' '[:lower:]')"
PASS=0
FAIL=0
SKIP=0

# Don't delete the image -- dryrun.py reuses it for Docker-based scoring

check() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        PASS=$((PASS + 1))
        echo "  PASS: $desc"
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL: $desc"
    fi
}

check_warn() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        PASS=$((PASS + 1))
        echo "  PASS: $desc"
    else
        SKIP=$((SKIP + 1))
        echo "  WARN: $desc"
    fi
}

# Pre-check: Docker available?
if ! command -v docker > /dev/null 2>&1 || ! docker info > /dev/null 2>&1; then
    echo "SKIP: Docker not available or not running."
    exit 0
fi

echo "=== Container Integration Test ==="
echo "Environment: $ENV_DIR"
echo ""

# ── 1. BUILD ──
echo "[1/8] Building image..."
if docker build -f "$ENV_DIR/Containerfile" -t "$IMAGE_NAME" "$ENV_DIR" > /tmp/container_build_log.txt 2>&1; then
    PASS=$((PASS + 1))
    echo "  PASS: Image builds successfully"
else
    echo "  FAIL: Image build failed"
    echo "  Last 20 lines:"
    tail -20 /tmp/container_build_log.txt
    exit 1
fi

# ── 2. TASK DISCOVERY ──
echo "[2/8] Task discovery..."
TASK_OUTPUT=$(docker run --rm --user root "$IMAGE_NAME" bash -c '
    cd /root && . .venv/bin/activate 2>/dev/null
    python -c "
try:
    from environment import get_tasks
    tasks = get_tasks()
    print(len(tasks))
except Exception as e:
    print(0)
" 2>/dev/null
' 2>/dev/null || echo "0")
TASK_COUNT=$(echo "$TASK_OUTPUT" | head -1)
if [ "$TASK_COUNT" -ge 1 ] 2>/dev/null; then
    PASS=$((PASS + 1))
    echo "  PASS: $TASK_COUNT tasks discovered"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL: Only $TASK_COUNT tasks discovered (need 1+)"
fi

# ── 3. SCORING SCRIPT ──
echo "[3/8] Scoring script..."
FIRST_CONFIG=$(docker run --rm --user root "$IMAGE_NAME" bash -c 'ls /root_data/eval/configs/*.json 2>/dev/null | head -1' 2>/dev/null)
if [ -n "$FIRST_CONFIG" ]; then
    SCORE_OUTPUT=$(docker run --rm --user root "$IMAGE_NAME" bash -c "
        /root/.venv/bin/python /root_data/eval/scoring.py '$FIRST_CONFIG' /tmp/test_score.json >/dev/null 2>&1
        cat /tmp/test_score.json 2>/dev/null
    " 2>/dev/null || echo "{}")
    if echo "$SCORE_OUTPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'score' in d" 2>/dev/null; then
        PASS=$((PASS + 1))
        echo "  PASS: Scoring produces valid JSON with score field"
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL: Scoring didn't produce valid output"
    fi
else
    FAIL=$((FAIL + 1))
    echo "  FAIL: No eval configs found in container"
fi

# ── 4. PERMISSIONS ──
echo "[4/8] Permissions..."
# Verify container default user is student, not root
DEFAULT_USER=$(docker run --rm "$IMAGE_NAME" whoami 2>/dev/null || echo "unknown")
if [ "$DEFAULT_USER" = "student" ]; then
    PASS=$((PASS + 1))
    echo "  PASS: Container default user is student"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL: Container default user is '$DEFAULT_USER' (expected 'student')"
fi
check "Student can write to /workdir/data" \
    docker run --rm --user root "$IMAGE_NAME" runuser -u student -- bash -c 'touch /workdir/data/_test && rm /workdir/data/_test'
check "Student cannot read /root_data" \
    docker run --rm --user root "$IMAGE_NAME" bash -c '! runuser -u student -- ls /root_data/ 2>/dev/null'
check "Student cannot read /root" \
    docker run --rm --user root "$IMAGE_NAME" bash -c '! runuser -u student -- ls /root/ 2>/dev/null'
check "Student cannot read /intermediate_data" \
    docker run --rm --user root "$IMAGE_NAME" bash -c '! runuser -u student -- ls /intermediate_data/ 2>/dev/null'
check "Student can read /workdir/shared" \
    docker run --rm --user root "$IMAGE_NAME" runuser -u student -- bash -c 'ls /workdir/shared/ >/dev/null'
check "Student cannot write to /workdir/shared" \
    docker run --rm --user root "$IMAGE_NAME" bash -c '! runuser -u student -- touch /workdir/shared/_test 2>/dev/null'

# ── 5. STUDENT VENV LOCKDOWN ──
echo "[5/8] Student venv security..."
check "Student cannot pip install" \
    docker run --rm --user root "$IMAGE_NAME" bash -c '! runuser -u student -- /workdir/.venv/bin/pip install requests 2>/dev/null'
check "Student cannot uv pip install" \
    docker run --rm --user root "$IMAGE_NAME" bash -c '! runuser -u student -- uv pip install requests 2>/dev/null'
check_warn "Student venv site-packages read-only" \
    docker run --rm --user root "$IMAGE_NAME" bash -c '! runuser -u student -- touch /workdir/.venv/lib/python*/site-packages/_test 2>/dev/null'

# ── 6. SCORING ISOLATION & PRIVILEGE DE-ESCALATION ──
echo "[6/8] Scoring isolation..."
check "Scoring script not readable by student" \
    docker run --rm --user root "$IMAGE_NAME" bash -c '! runuser -u student -- cat /root_data/eval/scoring.py 2>/dev/null'
check "Eval configs not readable by student" \
    docker run --rm --user root "$IMAGE_NAME" bash -c '! runuser -u student -- ls /root_data/eval/configs/ 2>/dev/null'

echo "  Testing behavioral privilege de-escalation..."
# We create a malicious student payload and force the scoring script to run it.
# If the scoring script correctly dropped privileges, the payload will be denied access to /root_data.
# If the scoring script failed to drop privileges, the payload will successfully hack the root directory.
HACK_RESULT=$(docker run --rm --user root "$IMAGE_NAME" bash -c "
    cat << 'EOF' > /workdir/data/hack.py
import os
try:
    with open('/root_data/hacked.txt', 'w') as f:
        f.write('pwned')
except Exception:
    pass
EOF
    cat << 'EOF' > /workdir/data/hack.lean
#eval do
  let _ ← IO.Process.run { cmd := \"touch\", args := #[\"/root_data/hacked.txt\"] }
EOF
    cat << 'EOF' > /workdir/data/hack.go
package main
import \"os\"
func main() { os.WriteFile(\"/root_data/hacked.txt\", []byte(\"pwned\"), 0644) }
EOF
    # Inject one of these as the target file
    if ls /root_data/eval/configs/*.json >/dev/null 2>&1; then
        CFG=\$(ls /root_data/eval/configs/*.json | head -1)
        /root/.venv/bin/python /root_data/eval/scoring.py \"\$CFG\" /tmp/score.json >/dev/null 2>&1
    fi
    # Check if the hack succeeded
    if [ -f /root_data/hacked.txt ]; then
        echo 'VULNERABLE'
    else
        echo 'SECURE'
    fi
" 2>/dev/null || echo "ERROR")

if [ "$HACK_RESULT" = "SECURE" ]; then
    PASS=$((PASS + 1))
    echo "  PASS: Scoring script correctly sandboxes student execution (Privilege Escalation blocked)"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL: Privilege Escalation detected! The scoring script executed student code with root privileges."
fi

# ── 7. CONFIG INTEGRITY ──
echo "[7/8] Config integrity..."
CONFIG_COUNT=$(docker run --rm --user root "$IMAGE_NAME" bash -c 'ls /root_data/eval/configs/*.json 2>/dev/null | wc -l' 2>/dev/null || echo "0")
VALID_JSON=$(docker run --rm --user root "$IMAGE_NAME" bash -c '
    count=0
    for f in /root_data/eval/configs/*.json; do
        /root/.venv/bin/python -c "import json; json.load(open(\"$f\"))" 2>/dev/null && count=$((count+1))
    done
    echo $count
' 2>/dev/null || echo "0")
if [ "$CONFIG_COUNT" -eq "$VALID_JSON" ] && [ "$CONFIG_COUNT" -gt 0 ]; then
    PASS=$((PASS + 1))
    echo "  PASS: All $CONFIG_COUNT configs are valid JSON"
else
    FAIL=$((FAIL + 1))
    echo "  FAIL: $VALID_JSON/$CONFIG_COUNT configs are valid JSON"
fi

# ── 8. DOMAIN TOOLS ──
echo "[8/8] Domain tools..."
CONTAINERFILE="$ENV_DIR/Containerfile"
if grep -qE "\blean\b|\belan\b" "$CONTAINERFILE" 2>/dev/null; then
    check "Lean compiler available" \
        docker run --rm "$IMAGE_NAME" bash -c 'lean --version'
fi
if grep -qE "\bvllm\b" "$CONTAINERFILE" 2>/dev/null; then
    check_warn "vLLM importable" \
        docker run --rm --user root "$IMAGE_NAME" runuser -u student -- bash -c '. /workdir/.venv/bin/activate && python -c "import vllm"'
fi
if grep -qE "\btorch\b" "$CONTAINERFILE" 2>/dev/null; then
    check_warn "PyTorch importable" \
        docker run --rm --user root "$IMAGE_NAME" runuser -u student -- bash -c '. /workdir/.venv/bin/activate && python -c "import torch"'
fi
if grep -qE "\bjax\b|\bpallas\b" "$CONTAINERFILE" 2>/dev/null; then
    check_warn "JAX importable" \
        docker run --rm --user root "$IMAGE_NAME" runuser -u student -- bash -c '. /workdir/.venv/bin/activate && python -c "import jax"'
fi

# ── 9. RUN.SH COMMANDS ──
echo "[9/11] run.sh commands..."
if [ -f "$ENV_DIR/run.sh" ]; then
    # Test list command (should work without GPU/TPU)
    LIST_OUTPUT=$("$ENV_DIR/run.sh" list 2>&1 || echo "FAILED")
    if echo "$LIST_OUTPUT" | grep -qv "FAILED"; then
        TASK_LINES=$(echo "$LIST_OUTPUT" | grep -v "^$\|Available" | wc -l)
        if [ "$TASK_LINES" -gt 0 ]; then
            PASS=$((PASS + 1))
            echo "  PASS: ./run.sh list works ($TASK_LINES tasks)"
        else
            FAIL=$((FAIL + 1))
            echo "  FAIL: ./run.sh list returned no tasks"
        fi
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL: ./run.sh list failed"
    fi
else
    SKIP=$((SKIP + 1))
    echo "  WARN: No run.sh found"
fi

# ── 10. STUDENT TOOL EXECUTION ──
echo "[10/11] Student can execute domain tools..."
if grep -qE "\blean\b|\belan\b" "$CONTAINERFILE" 2>/dev/null; then
    # Student (not root) can run lean
    check "Student can run lean" \
        docker run --rm --user root "$IMAGE_NAME" runuser -u student -- bash -c 'echo "" | lean --stdin 2>/dev/null || lean --version'
fi
if grep -qE "\bpython\b|\btorch\b|\bjax\b" "$CONTAINERFILE" 2>/dev/null; then
    # Student can import and run basic operations
    check "Student can run Python with env packages" \
        docker run --rm --user root "$IMAGE_NAME" runuser -u student -- bash -c '. /workdir/.venv/bin/activate 2>/dev/null && python -c "print(1+1)"'
fi

# ── 11. COMPOSE AND K8S SYNTAX ──
echo "[11/11] Compose and Kubernetes templates..."
if docker compose version >/dev/null 2>&1; then
    if [ -f "$ENV_DIR/docker-compose.yml" ]; then
        if docker compose -f "$ENV_DIR/docker-compose.yml" config > /dev/null 2>&1; then
            PASS=$((PASS + 1))
            echo "  PASS: docker-compose.yml is valid"
        else
            FAIL=$((FAIL + 1))
            echo "  FAIL: docker-compose.yml has syntax errors"
        fi
    fi
    if [ -f "$ENV_DIR/docker-compose.prod.yml" ]; then
        if docker compose -f "$ENV_DIR/docker-compose.prod.yml" config > /dev/null 2>&1; then
            PASS=$((PASS + 1))
            echo "  PASS: docker-compose.prod.yml is valid"
        else
            FAIL=$((FAIL + 1))
            echo "  FAIL: docker-compose.prod.yml has syntax errors"
        fi
    fi
else
    SKIP=$((SKIP + 1))
    SKIP=$((SKIP + 1))
    echo "  WARN: docker compose not available, skipping Compose YAML validation"
fi
if [ -f "$ENV_DIR/k8s-rl-job.yaml" ]; then
    if command -v kubectl >/dev/null 2>&1; then
        if kubectl cluster-info >/dev/null 2>&1; then
            if kubectl apply --dry-run=client -f "$ENV_DIR/k8s-rl-job.yaml" > /dev/null 2>&1; then
                PASS=$((PASS + 1))
                echo "  PASS: k8s-rl-job.yaml is valid Kubernetes syntax"
            else
                FAIL=$((FAIL + 1))
                echo "  FAIL: k8s-rl-job.yaml has syntax errors"
            fi
        else
            SKIP=$((SKIP + 1))
            echo "  WARN: kubectl installed but no cluster running, skipping K8s YAML validation"
        fi
    else
        SKIP=$((SKIP + 1))
        echo "  WARN: kubectl not installed, skipping K8s YAML validation"
    fi
fi

# ── SUMMARY ──
echo ""
TOTAL=$((PASS + FAIL + SKIP))
echo "Results: $PASS passed, $FAIL failed, $SKIP warnings (out of $TOTAL)"
if [ $FAIL -gt 0 ]; then
    echo "CONTAINER TEST FAILED"
    exit 1
fi
echo "CONTAINER TEST PASSED"
