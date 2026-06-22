FROM python:3.14-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY inboxconverge.py .

# Create non-root user for security
RUN addgroup -g 1000 inboxconverge && \
    adduser -D -u 1000 -G inboxconverge inboxconverge && \
    chown -R inboxconverge:inboxconverge /app

USER inboxconverge

# Run the application
CMD ["python", "-u", "inboxconverge.py"]
