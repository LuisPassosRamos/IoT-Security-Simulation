FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy common utilities
COPY common/ ./common/

# Copy sensor code based on build arg
ARG SENSOR_TYPE
COPY ${SENSOR_TYPE}/ ./sensor/

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose CoAP port
EXPOSE 5683/udp

# Default command (can be overridden)
CMD ["python", "sensor/main.py"]