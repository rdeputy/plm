# plm Dockerfile
# Product Lifecycle Management for Construction

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 plm && \
    useradd --uid 1000 --gid plm --shell /bin/bash --create-home plm

# Build stage
FROM base AS builder

# Copy all source first (needed for install)
COPY . .

RUN pip install --upgrade pip && \
    pip install build && \
    pip install .

# Production stage
FROM base AS production

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=plm:plm . .

# Create data directory
RUN mkdir -p /app/data && chown plm:plm /app/data

USER plm

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Default command
CMD ["uvicorn", "src.plm.main:app", "--host", "0.0.0.0", "--port", "8001"]
