# Dockerfile for Uplevel Financial Intelligence Agent
# Optimized for Google Cloud Run and Vertex AI Agent Engine

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY deployment/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY agents/ agents/
COPY mcps/ mcps/
COPY deployment/app.py .
COPY deployment/simple_app.py .
COPY deployment/deploy_agent.py .

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Expose port
EXPOSE $PORT

# Run the application
CMD ["python", "simple_app.py"]
