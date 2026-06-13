# Multi-stage build for production-optimized container image.
# Stage 1: Install dependencies in a builder stage.
FROM python:3.11-slim AS builder

# Set working directory for the build stage.
WORKDIR /app

# Copy only requirements first for Docker layer caching efficiency.
COPY requirements.txt .

# Install Python dependencies without cache for smaller image size.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production runtime image with minimal footprint.
FROM python:3.11-slim AS runtime

# Set working directory for the application.
WORKDIR /app

# Create non-root user for security best practices.
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from the builder stage.
COPY --from=builder /install /usr/local

# Copy application source code into the container.
COPY src/ ./src/

# Copy configuration files into the container.
COPY config/ ./config/

# Set Python path to include the source directory.
ENV PYTHONPATH=/app/src

# Set production environment by default.
ENV APP_ENV=prod

# Switch to non-root user for runtime security.
USER appuser

# Expose the application port for container networking.
EXPOSE 8000

# Health check for container orchestrator liveness probes.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health'); assert r.status_code == 200"

# Run the application with uvicorn ASGI server.
CMD ["uvicorn", "guardrails.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
