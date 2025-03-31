# NexusCore

A distributed container orchestration platform with scheduling, health monitoring, and fault tolerance capabilities.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Start the services:
   ```
   cd deployments
   docker-compose up -d
   ```

## API Documentation

Access the API documentation at http://localhost:8000/docs after starting the services.

## Scheduler

NexusCore uses a Best-Fit algorithm for scheduling pods on available nodes based on resource requirements.
