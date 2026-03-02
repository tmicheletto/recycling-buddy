# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Recycling Buddy is a full-stack ML application that classifies waste items from photos and provides council-specific recycling advice. It has three main components: `api/` (FastAPI), `model/` (PyTorch training pipeline), and `ui/` (React/Vite).

## Commands

### Top-level (from repo root)
```bash
make run          # Start all services via Docker Compose
make dev          # Rebuild images and start all services
make test         # Run tests for all components
make stop         # Stop all services
make logs         # Stream logs
make init-localstack  # Initialize LocalStack S3 bucket
```

### API (`cd api`)
```bash
uv run pytest                          # Run all tests
uv run pytest tests/test_inference.py  # Run a single test file
uv run ruff check .                    # Lint
uv run ruff format .                   # Format
```

### Model (`cd model`)
```bash
uv run pytest
uv run python -m recbuddy.train --s3-bucket recycling-buddy-training --output-dir artifacts/ --epochs 30 --seed 42
uv run python -m recbuddy.evaluate --artifact artifacts/efficientnet_b0_recycling_v1.safetensors --s3-bucket recycling-buddy-training --split test
```

### UI (`cd ui`)
```bash
npm run dev      # Dev server at http://localhost:5173
npm run build
npm run lint
```

## Architecture

### Layer interactions

```
UI (React/Vite :5173)
    ↓ HTTP
API (FastAPI :8000)
    ├── ClassificationModel  — EfficientNet-B0 loaded at startup from safetensors
    ├── GuidelinesService    — OpenAI-backed advice, in-memory cache (TTL 1 week)
    └── S3Service            — Training image uploads (LocalStack in dev)
          ↓
    S3 / LocalStack (:4566)
          ↑
Model training pipeline (standalone, not part of API runtime)
```

The `model/` component is a training-only pipeline. Its output (a `.safetensors` artifact) is consumed by the API at startup. The model is never imported at runtime — only the artifact file is.

### API startup

`api/src/main.py` uses a lifespan context manager to load `ClassificationModel` once on startup. If the artifact is missing, the app starts in a degraded state and `/predict` returns 503.

### Configuration (`api/src/config.py`)

Pydantic `BaseSettings` reads from `config/.env.<ENVIRONMENT>` (e.g. `config/.env.dev`). The `ENVIRONMENT` env var (default: `DEV`) selects the file. `.env.local` is gitignored and used for machine-local overrides.

Key settings: `model_artifact_path`, `guidelines_data_path`, `s3_endpoint_url`, `openai_api_key`, `cors_origins`.

### Guidelines advice flow (`api/src/guidelines.py`)

1. Look up `label_to_rny.json` (`data/label_to_rny.json`) for the classifier label → RNY slug + URL
2. Fetch the council's RNY page HTML as grounding context
3. Call GPT-4o-mini to extract structured `AdviceRecord`
4. Cache result in memory with configurable TTL

### Labels

`api/src/labels.py` is the single source of truth for the 67 waste category labels. Labels are lowercase with hyphens (e.g. `glass-bottles-jars`). The `data/label_to_rny.json` maps each label to its Recycling Near You slug and URL.

### Local development

Docker Compose runs `api`, `ui`, `model` (idle), and `localstack`. The API uses `S3_ENDPOINT_URL=http://localstack:4566` and dummy AWS credentials in dev. The `model/artifacts/` directory is mounted into the API container.

### Infrastructure

`infra/` contains Terraform for AWS deployment: App Runner (API), ECR (container registry), S3 (UI static hosting + training data), ALB. Deployed to `ap-southeast-2`.

## Testing notes

API tests use FastAPI's `TestClient` and `unittest.mock.patch` to mock S3 calls. No LocalStack required for unit tests. The `ENVIRONMENT` defaults to `DEV`, which resolves to `config/.env.dev`.
