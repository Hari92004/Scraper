FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port (default 7860 for Hugging Face / Render $PORT)
ENV PORT=7860
EXPOSE 7860

# Run FastAPI ASGI server
CMD ["python", "app.py"]
