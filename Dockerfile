# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-server.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-server.txt

# Copy application code
COPY server/ ./server/
COPY modules/ ./modules/
COPY cmds/ ./cmds/
COPY util/ ./util/
COPY strings/ ./strings/
COPY config.toml .

# Copy data files
COPY modules/data/ ./modules/data/

# Expose server port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV POSTGRES_HOST=postgres
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=fishing_bot
ENV POSTGRES_USER=bot_user
ENV POSTGRES_PASSWORD=bot_password

# Run the server
CMD ["python", "-c", "from server import run_server; run_server(host='0.0.0.0', port=8080)"]
