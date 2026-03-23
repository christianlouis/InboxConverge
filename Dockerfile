FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY pop3_forwarder.py .

# Create non-root user for security
RUN useradd -m -u 1000 forwarder && \
    chown -R forwarder:forwarder /app

USER forwarder

# Run the application
CMD ["python", "-u", "pop3_forwarder.py"]
