FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create directory for persistent data
RUN mkdir -p /data

# Expose port (Render will set PORT env var)
EXPOSE 8000

# Default DATABASE_URL for Docker (can be overridden)
ENV DATABASE_URL=sqlite:///./expenses.db

# Start command
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}

