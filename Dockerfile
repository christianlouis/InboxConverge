FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Pull in current distro security fixes from the base image package index.
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY inboxconverge.py .

# Create non-root user for security
RUN useradd -m -u 1000 inboxconverge && \
    chown -R inboxconverge:inboxconverge /app

USER inboxconverge

# Run the application
CMD ["python", "-u", "inboxconverge.py"]
