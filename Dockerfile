# Multi-stage build for smaller final image
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt requirements-dev.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Create directories for data persistence
RUN mkdir -p /app/data /app/output /app/config

# Set Python to run in unbuffered mode (better for Docker logs)
ENV PYTHONUNBUFFERED=1

# Default command - can be overridden
CMD ["python", "--version"]
