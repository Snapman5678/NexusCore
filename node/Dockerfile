FROM python:3.12-slim

WORKDIR /app

# Install system dependencies required for resource monitoring
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy just the heartbeat client code
COPY heartbeat_client.py .

# Start heartbeat client directly
CMD ["python", "heartbeat_client.py"]