# syntax=docker/dockerfile:1

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency specification and install production deps
COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

# Stage 2: Runtime image
FROM python:3.11-slim

WORKDIR /app

# Runtime system libraries required by PyTorch / Pillow
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy project source
COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT="/app/.venv"

CMD ["uv", "run", "python", "-c", "print('Model container ready — use docker-compose run model to execute training/evaluation')"]
