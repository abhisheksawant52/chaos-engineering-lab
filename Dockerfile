# syntax=docker/dockerfile:1

# ---- Builder stage -------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml requirements.txt README.md ./
COPY src ./src

# Build a wheel and install it plus runtime deps into an isolated prefix.
RUN python -m pip install --upgrade pip build \
    && python -m build --wheel --outdir /wheels \
    && pip install --prefix=/install /wheels/*.whl

# ---- Runtime stage -------------------------------------------------------
FROM python:3.12-slim AS runtime

# Copy the installed site-packages and the chaos-lab entrypoint.
COPY --from=builder /install /usr/local

# Ship the experiment manifests so the CLI can discover them by default.
WORKDIR /app
COPY experiments ./experiments

ENV EXPERIMENTS_DIR=/app/experiments \
    PYTHONUNBUFFERED=1

# Run as a non-root user.
RUN useradd --create-home --uid 10001 chaos \
    && chown -R chaos:chaos /app
USER chaos

ENTRYPOINT ["chaos-lab"]
CMD ["--help"]
