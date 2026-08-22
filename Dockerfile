FROM python:3.13.15-slim-bookworm@sha256:00faa2debb87529f9f0764e9491d8ba400a3678976616c3bd7cb193745ac20d1

ARG POWER_FRAMEWORK_COMMIT=13dd835be5f5a03b13cad4a627b0445b2451acf0
ARG POWER_FRAMEWORK_WHEEL_SHA256=f12ad02097448cd1b7663fc79681481013637d011ecde25a9085a899beb547e2
ARG SUITE_CONSTRAINTS_SHA256=33977cd71397cf4f52399d4923c067bd7f0f9199eebbf7351adeb095a1f30456

WORKDIR /app

# Install minimal OS build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install the exact suite-reviewed dependency set with semantic dense embeddings.
# Stable container must verify exact final public POWER wheel hash before installation.
COPY release/power-suite.constraints.txt /app/power-suite.constraints.txt
RUN test "$(sha256sum /app/power-suite.constraints.txt | awk '{print $1}')" = "$SUITE_CONSTRAINTS_SHA256" && \
    pip download --no-deps --dest /tmp/wheels "power-framework[semantic] @ https://github.com/weby-homelab/power-framework/releases/download/v3.7.4/power_framework-3.7.4-py3-none-any.whl" && \
    echo "${POWER_FRAMEWORK_WHEEL_SHA256}  /tmp/wheels/power_framework-3.7.4-py3-none-any.whl" | sha256sum -c - && \
    pip install --no-cache-dir --constraint /app/power-suite.constraints.txt "/tmp/wheels/power_framework-3.7.4-py3-none-any.whl[semantic]" && \
    rm -rf /tmp/wheels && \
    test "$(python3 -c 'import importlib.metadata; print(importlib.metadata.version("power-framework"))')" = "3.7.4" && \
    python3 -c "import importlib.util; assert importlib.util.find_spec('onnxruntime') is not None, 'semantic deps missing: onnxruntime'; assert importlib.util.find_spec('fastembed') is not None"

COPY pyproject.toml .
COPY src/ ./src/
COPY entrypoint.sh /app/entrypoint.sh

RUN pip install --no-cache-dir --constraint /app/power-suite.constraints.txt .


# Create dedicated non-root application user, group, and cache directories
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser && \
    mkdir -p /brain /data/cache /data/power_cache /tmp/cache /home/appuser/.cache && \
    chown -R appuser:appgroup /app /brain /data /tmp/cache /home/appuser && \
    chmod +x /app/entrypoint.sh

USER 10001:10001

ENV POWER_GUI_HOST=0.0.0.0
ENV POWER_GUI_PORT=8080
ENV POWER_GUI_VAULT_PATH=/brain
ENV POWER_GUI_AUTH_ENABLED=true
# /data is the named volume mount point; XDG_CACHE_HOME must point here
# so the FTS SQLite DB survives container restarts.
ENV XDG_CACHE_HOME=/data/cache
ENV POWER_CACHE_DIR=/data/power_cache
ENV POWER_ALLOW_DENSE_FALLBACK=1

EXPOSE 8080

# Extended start-period to allow FTS pre-warm on first boot with large vaults
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=5)"]

ENTRYPOINT ["/app/entrypoint.sh"]
