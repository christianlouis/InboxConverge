FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Pull in current distro security fixes before installing runtime packages.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
    --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Inject build metadata
ARG BUILD_DATE=""
ENV BUILD_DATE=${BUILD_DATE}

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Default command (can be overridden)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
