# Helios Cost Intelligence Service
# Multi-stage build for smaller image size
FROM python:3.11-slim AS builder

WORKDIR /build

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# Production stage
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Helios Cost Intelligence Service"
LABEL org.opencontainers.image.description="Resource cost analysis and optimization recommendations"
LABEL org.opencontainers.image.source="https://github.com/helios-platform/helios"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Install runtime dependencies only
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash helios && \
    chown -R helios:helios /app

# Copy application code
COPY --chown=helios:helios . ./cost_intelligence/

# Switch to non-root user
USER helios

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "cost_intelligence.app:app", "--host", "0.0.0.0", "--port", "8001"]
