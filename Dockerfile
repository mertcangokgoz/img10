FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN pip install uv && uv sync --frozen

# Copy application code
COPY src/ ./src/
COPY run.py .

# Create necessary directories
RUN mkdir -p uploads thumbnails config

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "run.py"]
