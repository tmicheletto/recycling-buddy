# Technology Stack

**Analysis Date:** 2026-02-26

## Languages

**Primary:**
- **Python 3.11** - Core runtime for API (`api/`) and ML training (`model/`), specified in Dockerfile and `.python-version`
- **TypeScript 5.9** - Frontend UI (`ui/`) with React, compiled to JavaScript
- **JavaScript (ES2020)** - Build and configuration tooling

**Secondary:**
- **YAML** - Docker Compose and configuration files

## Runtime

**Environment:**
- **Node.js 20 (Alpine)** - Frontend development and build (specified in `ui/Dockerfile`)
- **Python 3.11** - Backend services and ML model training (specified in Dockerfile targets)

**Package Managers:**
- **npm** (Node.js) - UI dependencies (`ui/package.json`)
- **uv** - Python package management for both API and model (used in Dockerfiles and `pyproject.toml`)
- **Lockfiles:**
  - `ui/package-lock.json` (npm)
  - `api/uv.lock` (uv)
  - `model/uv.lock` (uv)

## Frameworks

**Backend:**
- **FastAPI 0.128.0+** - RESTful API framework (`api/`)
  - Location: `api/src/main.py`
  - Middleware: CORSMiddleware for cross-origin requests
  - Lifespan management: Model loaded at app startup, released on shutdown

**Frontend:**
- **React 19.2.0** - UI library (`ui/src/`)
  - Uses React Hooks (useState, useEffect, useMemo, useRef)
  - Components: `PhotoCapture.tsx`, `ItemPicker.tsx`

**Build Tools:**
- **Vite 7.2.4** - Frontend build and dev server (`ui/`)
  - Config: `ui/vite.config.ts`
  - Enables React Fast Refresh via `@vitejs/plugin-react`

**Web Server:**
- **Uvicorn 0.40.0+** - ASGI server for FastAPI (`api/`)
  - Runs on port 8000 in development and production

## Key Dependencies

**Critical - ML/Inference:**
- **PyTorch** (version unspecified, CPU-only) - Deep learning framework for model training and inference
  - Uses CPU-only wheels on Linux from `https://download.pytorch.org/whl/cpu`
  - Used in both `api/` (inference) and `model/` (training)
- **torchvision** - Vision models and transforms (EfficientNet-B0 backbone)
- **safetensors 0.4.0+** - Model serialization format (artifact storage)
- **Pillow 12.0.0+** - Image loading and preprocessing

**Critical - API/Backend:**
- **FastAPI 0.128.0+** - HTTP framework
- **Pydantic v2** (via `pydantic-settings 2.12.0+`) - Data validation and settings management
- **Starlette** - ASGI toolkit (included in FastAPI)
- **python-multipart 0.0.22+** - File upload handling
- **Uvicorn 0.40.0+** - ASGI server

**Infrastructure:**
- **boto3 1.42.0+** - AWS SDK for S3 integration
  - Used in both `api/` (training image uploads) and `model/` (dataset downloads)

**Frontend:**
- **React 19.2.0** - UI library
- **React DOM 19.2.0** - DOM rendering

**Development - Python:**
- **pytest 9.0.0+** - Test framework (both `api/` and `model/`)
- **pytest-asyncio 1.3.0+** - Async test support (`api/`)
- **pytest-cov 4.1.0+** - Coverage reports (`model/`)
- **ruff 0.14.0+** - Linting and formatting
- **httpx 0.28.1+** - HTTP client for API testing (`api/`)
- **anyio 4.12.1+** - Async compatibility (`api/`)
- **pyrefly 0.19.0+** - Code intelligence (`api/` and `model/`)

**Development - Frontend:**
- **TypeScript 5.9** - Type checking
- **@vitejs/plugin-react 5.1.1+** - React integration
- **ESLint 9.39.1+** - Code linting
  - Flat config via `eslint.config.js`
  - Plugins: `typescript-eslint`, `react-hooks`, `react-refresh`
- **typescript-eslint 8.46.4+** - TypeScript ESLint support

## Configuration

**Environment Variables (API):**
- Location: `api/config/{ENVIRONMENT}.env` (loaded via `pydantic_settings`)
- Key vars:
  - `ENVIRONMENT` - Dev/Test/Prod mode
  - `S3_BUCKET` - Training dataset bucket name
  - `S3_ENDPOINT_URL` - AWS S3 endpoint (or LocalStack for dev)
  - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` - AWS credentials
  - `AWS_REGION` - AWS region
  - `CORS_ORIGINS` - CORS allowlist
  - `MODEL_ARTIFACT_PATH` - Path to model weights file
- Files present: `api/config/dev.env`, `api/config/test.env`

**Environment Variables (Frontend):**
- Location: `ui/config/` with `VITE_` and `API_` prefixes
- Files present: `ui/config/.env.dev`, `ui/config/.env.test`
- Docker env: `API_URL=http://localhost:8000` (dev)

**Type Checking:**
- **Pyright** (`api/pyrightconfig.json`, `model/pyproject.toml`) - Python type checking
  - API config: Sets import root to `api/` directory for proper imports
- **TypeScript** (`ui/tsconfig.json`, `ui/tsconfig.app.json`, `ui/tsconfig.node.json`) - Frontend type checking

**Code Style:**
- **Ruff** (`model/pyproject.toml`) - Python formatter/linter
  - Line length: 88
  - Rules: E (errors), F (PyFlakes), I (imports)

## Platform Requirements

**Development:**
- Python 3.11
- Node.js 20
- npm (included with Node.js)
- uv package manager (installed in Docker via `ghcr.io/astral-sh/uv:latest`)

**Production:**
- **Container Runtime:** Docker / Docker Compose
- **Deployment Target:** AWS ECS Fargate
  - Task definition: `api/task-definition.json`
  - CPU: 256 units
  - Memory: 512 MB
  - Region: ap-southeast-2
  - CloudWatch Logs: `/ecs/recycling-buddy-api`
  - Roles: IAM execution role and task role (ARNs in task definition)

**Local Development Stack:**
- Docker Compose with services: `api`, `ui`, `model`, `localstack` (S3 mock)
- LocalStack on port 4566 for AWS service emulation

---

*Stack analysis: 2026-02-26*
