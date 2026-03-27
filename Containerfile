########################################################################
# hw-cbmc-demo: Formal Hardware Verification RL Environment
# Multi-stage build: compile ebmc from source, then minimal runner stage
########################################################################

# ── Stage 1: Build ebmc from source ──────────────────────────────────
FROM ubuntu:24.04 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ flex bison make curl patch git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone --depth=1 https://github.com/diffblue/hw-cbmc.git && \
    cd hw-cbmc && \
    git submodule update --init lib/cbmc

WORKDIR /build/hw-cbmc
RUN make -j$(nproc) -C lib/cbmc/src minisat2-download
RUN make -j$(nproc) -C src

# Verify binary was produced
RUN test -f src/ebmc/ebmc && src/ebmc/ebmc --version

# ── Stage 2: Minimal runner stage ────────────────────────────────────
FROM ubuntu:24.04

ENV UV_VERSION=0.8.15 \
    UV_INSTALL_DIR=/opt/uv \
    PATH="/opt/uv/:$PATH" \
    UV_CACHE_DIR="/tmp/uv_cache" \
    UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    PYTHON_VERSION=3.12.11 \
    STUDENT_WORKDIR=/workdir \
    ROOT_WORKDIR=/root

# Install ebmc binary from builder stage
COPY --from=builder /build/hw-cbmc/src/ebmc/ebmc /usr/local/bin/ebmc
RUN chmod 755 /usr/local/bin/ebmc

# Install runtime dependencies + Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 libgcc-s1 \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh && \
    rm -rf /tmp/* /var/tmp/*

RUN uv python install ${PYTHON_VERSION}

# Set up student user (uid 1000)
# Ubuntu 24.04 may already have uid/gid 1000 — handle gracefully
RUN bash -c '\
  if ! getent group 1000 > /dev/null 2>&1; then \
    groupadd -g 1000 student; \
  else \
    EXISTING_GROUP=$(getent group 1000 | cut -d: -f1); \
    if [ "$EXISTING_GROUP" != "student" ]; then \
      groupmod -n student "$EXISTING_GROUP"; \
    fi; \
  fi && \
  if ! getent passwd 1000 > /dev/null 2>&1; then \
    useradd -m -u 1000 -g 1000 student; \
  else \
    EXISTING_USER=$(getent passwd 1000 | cut -d: -f1); \
    if [ "$EXISTING_USER" != "student" ]; then \
      usermod -l student "$EXISTING_USER"; \
    fi; \
  fi && \
  gpasswd -d student root 2>/dev/null || true'

# Working directory for student
RUN mkdir -p ${STUDENT_WORKDIR} && chown -R 1000:1000 ${STUDENT_WORKDIR}

# Create student virtual environment
USER student
WORKDIR ${STUDENT_WORKDIR}
COPY --chown=student student_requirements.txt ${STUDENT_WORKDIR}/student_requirements.txt
RUN uv venv --python=${PYTHON_VERSION} \
    && uv pip install -r student_requirements.txt \
    && rm -rf ${UV_CACHE_DIR}/*

# Copy student data (circuit files with bugs)
COPY --chown=student student_data/ ${STUDENT_WORKDIR}/data/

# Switch to root for protected data
USER root
WORKDIR ${ROOT_WORKDIR}

# Create protected data directories
RUN mkdir /root_data && chmod 0700 /root_data && \
    mkdir /intermediate_data && chmod 700 /intermediate_data

# Copy root data (scoring scripts — student CANNOT access)
COPY --chown=root root_data/ /root_data/

# Copy intermediate data
COPY --chown=root intermediate_data/ /intermediate_data/

# Copy shared data (student can read, not modify)
COPY --chown=root shared_data/ ${STUDENT_WORKDIR}/shared/

# Lock down shared directory (read-only for student)
RUN chmod 1755 ${STUDENT_WORKDIR}/shared && \
    find ${STUDENT_WORKDIR}/shared -type f -exec chmod 444 {} \; && \
    find ${STUDENT_WORKDIR}/shared -type d -exec chmod 555 {} \;

# Install environment code in root venv
COPY pyproject.toml ${ROOT_WORKDIR}/
COPY src/ ${ROOT_WORKDIR}/src/
RUN cd ${ROOT_WORKDIR} && uv venv --python=${PYTHON_VERSION} && \
    uv pip install . && rm -rf ${UV_CACHE_DIR}/*

# Student virtual environment
ENV VIRTUAL_ENV=${STUDENT_WORKDIR}/.venv \
    PATH="${STUDENT_WORKDIR}/.venv/bin:$PATH"

# Lock down root-only data directories
RUN chmod 0700 ${ROOT_WORKDIR} /root_data /intermediate_data

# Security: prevent student from modifying their venv
RUN chmod -R a-w ${STUDENT_WORKDIR}/.venv/lib/ && \
    chmod -R a-w ${STUDENT_WORKDIR}/.venv/bin/pip* 2>/dev/null || true
RUN rm -f ${STUDENT_WORKDIR}/.venv/bin/uv 2>/dev/null || true

# Build-time validation: verify permission model
RUN echo "Checking permissions..." && \
    test "$(stat -c '%a' /root_data)" = "700" && \
    test "$(stat -c '%a' /intermediate_data)" = "700" && \
    echo "Permission model OK"

# Build-time validation: verify configs parse and ebmc is available
RUN python3 -c "\
import json, glob; \
configs = glob.glob('/root_data/eval/configs/*.json'); \
[json.loads(open(f).read()) for f in configs]; \
print(f'Validated {len(configs)} configs')"

RUN ebmc --version && echo "ebmc binary OK"

# WARMUP: Run ebmc --version one more time in the final layer to warm
# dynamic linker caches. This eliminates the cold-start timing spike
# (~0.5s) that would otherwise affect the first scoring call.
RUN ebmc --version > /dev/null 2>&1 && echo "ebmc warmup complete"

# IMPORTANT: Final USER must be student — scoring runs with --user root
USER student
WORKDIR ${STUDENT_WORKDIR}
