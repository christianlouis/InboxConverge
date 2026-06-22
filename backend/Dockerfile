FROM python:3.14-alpine

# Set working directory
WORKDIR /app

# Install system dependencies without Debian's vulnerable util-linux/mount base package.
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-client \
    postgresql-dev

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
