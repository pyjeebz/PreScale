FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code as a package
COPY . /app/cost_intelligence/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8081/health').raise_for_status()"

# Run application
CMD ["python", "-m", "uvicorn", "cost_intelligence.app:app", "--host", "0.0.0.0", "--port", "8081"]
