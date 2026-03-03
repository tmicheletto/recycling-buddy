FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy recbuddy package (path dependency of the api)
# Only the package source is needed — not the full model directory
COPY model/pyproject.toml /model/pyproject.toml
COPY model/README.md /model/README.md
COPY model/recbuddy/ /model/recbuddy/

# Copy api project files and install dependencies
COPY api/pyproject.toml .
COPY api/uv.lock .
RUN uv sync --frozen

# Copy remaining api source
COPY api/ .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
