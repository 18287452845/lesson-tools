# Backend Dockerfile for Lesson Plan Generator
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (including curl for health check)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend directory
COPY backend/ /app/backend/

# Copy requirements and install dependencies
COPY backend/requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create storage directories
RUN mkdir -p /app/storage/templates \
    /app/storage/uploads \
    /app/storage/outputs \
    /app/storage/exports

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check using curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
