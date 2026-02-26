# External Integrations

**Analysis Date:** 2026-02-26

## APIs & External Services

**None currently in use.** The application is designed for self-contained inference; no third-party classification or ML APIs are consumed.

## Data Storage

**Databases:**
- **Not applicable** - Application is stateless. No database is used for prediction results or user data persistence.

**File Storage (S3 - Object Storage):**
- **AWS S3** (or LocalStack in development)
  - Purpose: Storing training images uploaded via `/upload` endpoint for future model retraining
  - Implementation: `api/src/services/s3.py`
  - Client: `boto3 1.42.0+`
  - Configuration:
    - `S3_BUCKET` env var: Bucket name (default: `recycling-buddy-training`)
    - `S3_ENDPOINT_URL` env var: AWS endpoint or LocalStack URL
    - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` env vars: Credentials
    - `AWS_REGION` env var: Region (default: `us-east-1`)
  - Upload method: `S3Service.upload_training_image()` in `api/src/main.py` `/upload` endpoint
  - Key structure: `{label}/{uuid}_{timestamp}.{ext}` (e.g., `recyclable/abc-123_20260226_143000.jpeg`)
  - Detection: Image format detected from magic bytes (JPEG, PNG, bin fallback)

**Model Artifacts:**
- **Local filesystem** in Docker volume
  - Path: `/app/model/artifacts/efficientnet_b0_recycling_v1.safetensors`
  - Format: safetensors (PyTorch weights)
  - Mounted: `docker-compose.yml` mounts `./model:/app/model` into API service

**Caching:**
- **In-process** - Model loaded once at FastAPI lifespan startup, cached in `app.state.model`
- No external caching service (Redis, Memcached, etc.)

## Authentication & Identity

**Auth Provider:**
- **None** - Application has no authentication layer
- All endpoints are publicly accessible (no API keys, OAuth, JWT, etc.)

**CORS Policy:**
- Implemented via `FastAPI.add_middleware(CORSMiddleware)`
- Allowlist: `CORS_ORIGINS` env var (comma-separated origins)
- Default: `http://localhost:5173` (local development)
- Credentials: Allowed
- Methods: All (`["*"]`)
- Headers: All (`["*"]`)

## Monitoring & Observability

**Error Tracking:**
- **None** - No external error tracking service configured

**Logging:**
- **Console/stdout**
  - Framework: Python `logging` module
  - Configuration: `logging.basicConfig(level=logging.INFO)` in `api/src/main.py`
  - Log format: Structured JSON emitted for prediction events
    - Example from `api/src/main.py` line 151-161: Prediction logs include event type, timestamp, label, confidence
  - Logs routed to CloudWatch Logs in production via ECS task definition

**Structured Logging:**
- Predictions logged as JSON: `{"event": "prediction", "timestamp": "...", "predicted_label": "...", "confidence": ...}`
- S3 uploads logged with HTTP status and request ID

## CI/CD & Deployment

**Hosting:**
- **AWS ECS Fargate** (production)
  - Task definition: `api/task-definition.json`
  - Container image: ECR (URI placeholder in task definition)
  - Task size: 256 CPU, 512 MB memory
  - Region: ap-southeast-2
  - Execution role: `arn:aws:iam::646385694251:role/recycling-buddy-ecs`
  - Task role: `arn:aws:iam::646385694251:role/recycling-buddy-api`

**CI Pipeline:**
- **Not detected** - No GitHub Actions, GitLab CI, Jenkins, or other CI config files present
- Build & test execution: Manual or via orchestrator (not in codebase)

**Container Registry:**
- **Amazon ECR** (implied by task definition)
  - Build via Dockerfile in each service directory
  - Images: `api/Dockerfile`, `ui/Dockerfile`, `model/Dockerfile`

**Local Development Deployment:**
- **Docker Compose** (`docker-compose.yml`)
  - Services: `api` (port 8000), `ui` (port 5173), `model`, `localstack` (port 4566)
  - Volumes: Live reload for development
  - Environment: LocalStack endpoints for S3 emulation

## Environment Configuration

**Required Environment Variables (API):**

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `ENVIRONMENT` | No | DEV | Config file selector (dev/test/prod) |
| `S3_BUCKET` | No | `recycling-buddy-training` | Training dataset bucket |
| `S3_ENDPOINT_URL` | No | None | AWS endpoint or LocalStack URL |
| `AWS_ACCESS_KEY_ID` | No | None | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | No | None | AWS secret key |
| `AWS_REGION` | No | `us-east-1` | AWS region |
| `CORS_ORIGINS` | No | `http://localhost:5173` | CORS allowlist |
| `MODEL_ARTIFACT_PATH` | No | `model/artifacts/efficientnet_b0_recycling_v1.safetensors` | Model weights path |
| `PYTHONUNBUFFERED` | No | (set to 1 in Docker) | Unbuffered output |

**Required Environment Variables (Frontend):**

| Variable | Required | Purpose |
|----------|----------|---------|
| `API_URL` | No | Backend API base URL (default inferred from `localhost:8000`) |

**Secrets Location:**
- Docker Compose: Hard-coded test credentials in `docker-compose.yml` (LocalStack)
- ECS task definition: Secrets passed via task definition (not shown; would use `secretsReference` in production)
- Local: Environment files in `api/config/` and `ui/config/`

## Webhooks & Callbacks

**Incoming Webhooks:**
- **None** - No webhook endpoints

**Outgoing Webhooks:**
- **None** - No external systems notified

## Data Flow

**Prediction Request:**
1. Frontend (`ui/src/services/api.ts`) sends image to `POST /predict`
2. FastAPI receives file upload, validates MIME type
3. Image bytes passed to `ClassificationModel.predict()` (loaded at startup)
4. PyTorch inference on EfficientNet-B0 backbone + classifier head
5. Top 3 predictions returned as `PredictionResponse`
6. Structured log emitted with result

**Training Image Upload:**
1. Frontend sends base64 image + label to `POST /upload`
2. API decodes base64, validates image magic bytes
3. `S3Service.upload_training_image()` uploads to S3 bucket
4. Response includes S3 key for reference

**Model Serving:**
- Model loaded once at app startup via `ClassificationModel.from_artifact()`
- Weights stored in safetensors format
- Inference is thread-safe (model.eval() + torch.inference_mode())
- Runs on CPU (no GPU required)

---

*Integration audit: 2026-02-26*
