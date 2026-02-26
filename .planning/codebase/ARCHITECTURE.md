# Architecture

**Analysis Date:** 2026-02-26

## Pattern Overview

**Overall:** Three-tier ML service architecture with decoupled model training, API inference, and frontend UI. Each component is independently containerizable and communicates over HTTP/REST and S3 APIs.

**Key Characteristics:**
- Monorepo structure with three independent services (model, api, ui)
- Transfer learning pipeline (EfficientNet-B0) decoupled from serving
- Stateless FastAPI inference server with thread-safe model loading
- React frontend consuming prediction and label-discovery APIs
- S3-centric dataset management for training data versioning

## Layers

**Presentation Layer (UI):**
- Purpose: User-facing image capture and upload interface; result display
- Location: `ui/src/`
- Contains: React components, custom hooks, API client, type definitions
- Depends on: API service (`/labels`, `/upload`)
- Used by: End users (browsers)

**API Layer:**
- Purpose: HTTP request handling, validation, inference orchestration
- Location: `api/src/main.py` (FastAPI app), `api/src/` (services)
- Contains: Route handlers, Pydantic request/response models, S3 upload service
- Depends on: ClassificationModel (inference), S3Service (storage), Labels registry
- Used by: UI, external clients

**Model/Inference Layer:**
- Purpose: Stateless image classification using loaded PyTorch model
- Location: `api/src/inference.py` (ClassificationModel class)
- Contains: Image decoding, tensor transforms, PyTorch forward pass
- Depends on: PyTorch, Pillow, safetensors, ImageNet normalization
- Used by: `/predict` route

**Training Pipeline:**
- Purpose: Dataset management, two-phase transfer learning, checkpoint persistence
- Location: `model/src/` (dataset.py, train.py, transforms.py, evaluate.py)
- Contains: S3 download, ImageFolder splits, training loops, evaluation metrics
- Depends on: boto3 (S3), torchvision (transforms, ImageFolder), PyTorch
- Used by: ML engineers (CLI), Docker training jobs

**Data Storage:**
- Purpose: Version training datasets and store uploaded training images
- Technology: S3 (AWS or LocalStack in dev)
- Structure: `s3://recycling-buddy-training/<label>/<uuid>_<timestamp>.<ext>`
- Used by: Model training (download), API (upload)

## Data Flow

**Inference Path (UI → API → Model):**

1. User captures/selects image in PhotoCapture component (`ui/src/components/PhotoCapture.tsx`)
2. React hook converts image to base64 (`ui/src/hooks/useImageUpload.ts::fileToBase64()`)
3. POST request to `/upload` with base64 + label via `ui/src/services/api.ts::uploadImage()`
4. FastAPI validates label against `api/src/labels.py::ALL_LABELS` frozenset
5. API decodes base64 → bytes and validates image magic bytes
6. S3Service uploads bytes to `s3://recycling-buddy-training/<label>/<uuid>_<timestamp>.<ext>`
7. API returns UploadResponse with S3 key

**Label Discovery:**

1. UI component mounts, calls `useLabels()` hook
2. Hook calls `fetchLabels()` → GET `/labels`
3. API handler reads `api/src/labels.py::ALL_LABELS_LIST` (67 items)
4. Converts to LabelItem list with display names
5. Returns LabelsResponse with items and total_count

**Model Training Pipeline (Batch):**

1. Trainer downloads dataset: `model/src/dataset.py::WasteDataset.download()`
   - Lists all objects in S3 bucket via boto3 paginator
   - Downloads to `data/<label>/<filename>` (idempotent)
2. Splits data: `WasteDataset.get_splits(val_frac=0.15, test_frac=0.15, seed=42)`
   - Returns train, val, test datasets with different transforms
   - Training uses augmentation (via `training_transform()`)
3. Runs two-phase training in `model/src/train.py::train()`
   - Phase 1: Backbone frozen, head-only AdamW for 5 epochs
   - Phase 2: Full fine-tune with differential learning rates, SequentialLR (warmup→cosine), Mixup
4. Saves checkpoints after each epoch to `model/checkpoints/`
5. Saves final artifact to `model/artifacts/efficientnet_b0_recycling_v{N}.safetensors`

**State Management:**

- **Model state:** Loaded once at API startup via FastAPI lifespan, stored in `app.state.model` (shared across requests)
- **Model thread-safety:** No shared mutable state; each `predict()` call creates fresh tensors, uses `torch.inference_mode()`
- **Training reproducibility:** All random seeds set via `_set_seeds(seed)` in train.py
- **Data versioning:** S3 bucket is single source of truth; no local state in API

## Key Abstractions

**ClassificationModel:**
- Purpose: Wraps PyTorch EfficientNet-B0, provides thread-safe inference interface
- Examples: `api/src/inference.py::ClassificationModel`
- Pattern: Class-based with `from_artifact(path)` factory method; `predict(image_bytes) → ClassificationResult`

**CategoryPrediction / ClassificationResult:**
- Purpose: Value objects for model output
- Examples: `api/src/inference.py::CategoryPrediction`, `ClassificationResult`
- Pattern: Frozen dataclasses; top_prediction and alternatives (exactly 3 items)

**Pydantic Models (Request/Response):**
- Purpose: HTTP contract validation
- Examples: `api/src/main.py::UploadRequest`, `PredictionResponse`, `LabelsResponse`
- Pattern: Inherit from `BaseModel`, use `@field_validator` decorators

**S3Service:**
- Purpose: Encapsulates boto3 S3 client, handles upload path generation
- Examples: `api/src/services/s3.py::S3Service`
- Pattern: Constructor injection of bucket name and credentials; `upload_training_image(data, label) → s3_key`

**WasteDataset:**
- Purpose: Manages S3 dataset downloads and PyTorch dataset splits
- Examples: `model/src/dataset.py::WasteDataset`
- Pattern: Constructor stores S3 config; lazy download and split generation; integrates with torchvision ImageFolder

**Labels Registry:**
- Purpose: Single source of truth for valid waste item categories
- Examples: `api/src/labels.py::ALL_LABELS_LIST` (list), `ALL_LABELS` (frozenset)
- Pattern: Module-level constants; validation functions `is_valid_label()`, `is_s3_safe()`

## Entry Points

**API:**
- Location: `api/src/main.py`
- Triggers: Docker container start or local `uvicorn src.main:app`
- Responsibilities: FastAPI app initialization, lifespan management (load model), CORS setup, route definition

**Training CLI:**
- Location: `model/src/train.py::_parse_args()` and main block
- Triggers: `python -m src.train --s3-bucket ... --output-dir ...`
- Responsibilities: Parse CLI args, initialize WasteDataset, run two-phase training, save artifact

**Evaluation CLI:**
- Location: `model/src/evaluate.py` (CLI entry point)
- Triggers: `python -m src.evaluate --artifact ... --s3-bucket ...`
- Responsibilities: Load artifact, download dataset, compute per-category accuracy, detect confusion pairs

**UI:**
- Location: `ui/src/main.tsx`
- Triggers: Vite dev server or Nginx production build
- Responsibilities: Mount React app, hydrate App component

## Error Handling

**Strategy:** Fail fast with meaningful error messages; use HTTP status codes for API; log structured JSON for observability.

**Patterns:**

- **Image validation:** Check magic bytes (JPEG: `FF D8 FF`, PNG: `89 50 4E 47`) before processing (`api/src/main.py::_is_valid_image()`)
- **HTTP errors:** Raise `HTTPException(status_code=..., detail=...)` with plain English messages
- **Inference errors:** Wrap PIL/PyTorch exceptions as `ValueError` in `ClassificationModel._decode()`; caught by route handler and converted to 400/500
- **Model loading:** Explicit `FileNotFoundError` if artifact missing; logged at startup via lifespan
- **S3 errors:** Wrap `botocore.exceptions.ClientError` as `RuntimeError` in dataset download; propagate to trainer
- **Structured logging:** Prediction events logged as JSON via `logger.info(json.dumps({...}))` (no image data)

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module
- Level: INFO for lifecycle events (model loaded, prediction, S3 upload); ERROR for exceptions
- Structured: JSON format for prediction events (timestamp, label, confidence); plain format for lifecycle

**Validation:**
- Request validation: Pydantic models with `@field_validator` decorators (label must be in ALL_LABELS)
- Image validation: Magic byte checks before decode; PIL exception handling
- S3 safety: Labels validated against regex `^[a-z][a-z0-9-]*$` before use as key prefixes

**Authentication:**
- API: CORS enabled for frontend origin; no auth tokens required (public endpoint)
- S3: AWS credentials (access key + secret) injected via environment or boto3 defaults

**Concurrency:**
- API: Single model instance shared across async requests via `app.state.model`
- Thread pool: Image processing (`predict()` call) run in thread pool via `run_in_threadpool()` to avoid blocking event loop
- PyTorch: Thread counts set at module load time (`torch.set_num_interop_threads(1)`, `torch.set_num_threads(4)`)

---

*Architecture analysis: 2026-02-26*
