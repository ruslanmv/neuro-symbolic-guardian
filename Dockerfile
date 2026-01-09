# Multi-stage Dockerfile for Neuro-Symbolic Guardian
# Optimized for production deployment with minimal size

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Install UV
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml .python-version ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install --no-cache -e .

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 guardian && \
    mkdir -p /app /app/logs && \
    chown -R guardian:guardian /app

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=guardian:guardian src/ /app/src/
COPY --chown=guardian:guardian README.md LICENSE /app/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AEGIS_ENV=production

# Switch to non-root user
USER guardian

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command (MCP server)
CMD ["ns-guardian", "--mode", "mcp"]

# Expose port for API mode (optional)
EXPOSE 8000

# Labels
LABEL org.opencontainers.image.title="Neuro-Symbolic Guardian" \
      org.opencontainers.image.description="Production-ready MCP server for LLM verification with symbolic logic" \
      org.opencontainers.image.version="2.0.0" \
      org.opencontainers.image.authors="Ruslan Magana Vsevolodovna" \
      org.opencontainers.image.licenses="Apache-2.0"
