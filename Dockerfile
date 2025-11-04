# Multi-stage Docker build for optimized production image

# Stage 1: Builder - Install dependencies and build wheels
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt gunicorn

# Stage 2: Runtime - Create lightweight production image
FROM python:3.11-slim as runtime

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY backend/ .

# Create necessary directories with proper permissions
RUN mkdir -p /var/log/gunicorn /var/run/gunicorn /app/cache && \
    chown -R appuser:appuser /var/log/gunicorn /var/run/gunicorn /app/cache

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden by docker-compose)
CMD ["gunicorn", "--config", "gunicorn.conf.py", "main:app"]

# Labels for metadata
LABEL maintainer="Learning App Team" \
      version="1.0.0" \
      description="Production container for Learning App FastAPI backend"