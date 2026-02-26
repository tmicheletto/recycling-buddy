# Codebase Structure

**Analysis Date:** 2026-02-26

## Directory Layout

```
recycling-buddy/
├── api/                          # FastAPI backend service
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app, route handlers, Pydantic models
│   │   ├── config.py             # Settings (Pydantic BaseSettings)
│   │   ├── labels.py             # Label registry (67 waste categories)
│   │   ├── inference.py          # ClassificationModel, inference logic
│   │   └── services/
│   │       ├── __init__.py
│   │       └── s3.py             # S3Service for uploading training images
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_predict_endpoint.py       # POST /predict integration tests
│   │   ├── test_upload.py                 # POST /upload integration tests
│   │   ├── test_labels.py                 # GET /labels unit tests
│   │   ├── test_labels_data.py            # Label registry validation tests
│   │   └── test_inference.py              # ClassificationModel.predict() unit tests
│   ├── Dockerfile                # API container (Python 3.11 + uv)
│   └── requirements.txt          # Python dependencies
├── model/                        # ML training pipeline
│   ├── src/
│   │   ├── __init__.py
│   │   ├── dataset.py            # WasteDataset: S3 download + train/val/test splits
│   │   ├── transforms.py         # Image transforms (training and inference pipelines)
│   │   ├── train.py              # Two-phase training loop + CLI entry point
│   │   └── evaluate.py           # Evaluation metrics + CLI entry point
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py           # Pytest fixtures (mock S3, temporary directories)
│   │   ├── test_dataset.py       # WasteDataset unit tests
│   │   ├── test_train.py         # Training loop unit tests
│   │   └── test_evaluate.py      # Evaluation unit tests
│   ├── artifacts/                # Trained model artifacts (gitignored)
│   │   └── efficientnet_b0_recycling_v1.safetensors  # Latest trained model
│   ├── checkpoints/              # Per-epoch safetensors checkpoints (gitignored)
│   ├── Dockerfile                # Model container (Python 3.11 + PyTorch + uv)
│   └── pyproject.toml            # uv project config and dependencies
├── ui/                           # React frontend
│   ├── src/
│   │   ├── App.tsx               # Root component (renders PhotoCapture)
│   │   ├── main.tsx              # React entry point
│   │   ├── App.css
│   │   ├── components/
│   │   │   ├── PhotoCapture.tsx  # Multi-phase image capture/upload flow
│   │   │   ├── PhotoCapture.css
│   │   │   └── ItemPicker.tsx    # Label selection dropdown/list
│   │   ├── hooks/
│   │   │   ├── useImageUpload.ts # Image upload state + base64 conversion
│   │   │   └── useLabels.ts      # Fetch labels from /labels endpoint
│   │   ├── services/
│   │   │   └── api.ts            # HTTP client (fetchLabels, uploadImage)
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript interfaces (LabelsResponse, UploadResponse)
│   │   └── index.css
│   ├── public/                   # Static assets (favicon, etc.)
│   ├── Dockerfile                # UI container (Node + Vite)
│   ├── package.json              # npm dependencies
│   ├── tsconfig.json             # TypeScript config
│   ├── tsconfig.app.json         # App-specific TypeScript config
│   ├── tsconfig.node.json        # Node/Vite TypeScript config
│   └── vite.config.ts            # Vite build config
├── .github/
│   └── workflows/                # CI/CD workflows
├── .planning/
│   └── codebase/                 # GSD mapping documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
├── .specify/                     # Project specification templates and memory
├── localstack-data/              # LocalStack S3 persistence (gitignored)
├── docker-compose.yml            # Service orchestration (api, ui, model, localstack)
├── Makefile                      # Development commands (setup, run, dev, test, etc.)
├── CLAUDE.md                     # Project instructions (auto-generated from feature plans)
├── README.md                     # Project overview and quick start
├── IMPLEMENTATION_SUMMARY.md     # Previous implementation summary
├── MAKEFILE_GUIDE.md             # Makefile documentation
├── QUICKSTART_UPLOAD.md          # Dataset upload guide
└── .gitignore                    # Excludes artifacts, venv, node_modules, etc.
```

## Directory Purposes

**api/**
- Purpose: FastAPI backend service for image classification and training data upload
- Contains: Route handlers, Pydantic models, inference orchestration, S3 integration
- Key files: `src/main.py` (app), `src/inference.py` (model), `src/services/s3.py` (upload)

**api/src/**
- Purpose: Python source code for API
- Contains: Request handlers, response models, configuration, business logic
- Key files: `main.py` (FastAPI app definition), `inference.py` (ClassificationModel)

**api/tests/**
- Purpose: Unit and integration tests for API
- Contains: Test fixtures, mock models, integration tests
- Key files: All test files use `TestClient` with mocked ClassificationModel

**model/**
- Purpose: ML training pipeline for EfficientNet-B0 classifier
- Contains: Dataset management, training loops, evaluation logic
- Key files: `src/train.py` (training CLI), `src/dataset.py` (S3 download and splits)

**model/src/**
- Purpose: Python training code
- Contains: Dataset loading, data transforms, training/evaluation logic
- Key files: `train.py` (two-phase training), `dataset.py` (WasteDataset)

**model/tests/**
- Purpose: Unit tests for training pipeline
- Contains: Dataset mocking, training logic tests
- Key files: Uses `conftest.py` for fixtures; tests use mocked S3 and temporary directories

**model/artifacts/**
- Purpose: Trained model weights storage
- Contains: `.safetensors` model files named `efficientnet_b0_recycling_v{N}.safetensors`
- Generated: Yes (by training pipeline)
- Committed: No (gitignored; typically downloaded from S3 or built via training)

**ui/**
- Purpose: React frontend for image upload and label selection
- Contains: React components, hooks, API client, TypeScript types
- Key files: `src/App.tsx` (root), `src/components/PhotoCapture.tsx` (main flow)

**ui/src/**
- Purpose: React source code
- Contains: Components, hooks, API client, types
- Key files: `App.tsx` (renders PhotoCapture), `services/api.ts` (HTTP client)

**ui/src/components/**
- Purpose: Reusable React components
- Contains: PhotoCapture (multi-phase flow), ItemPicker (label selection)
- Key files: `PhotoCapture.tsx` (main component with state machine phases)

**ui/src/hooks/**
- Purpose: Custom React hooks for state management and API calls
- Contains: useImageUpload (upload state), useLabels (label fetching)
- Key files: `useImageUpload.ts` (base64 conversion + upload), `useLabels.ts` (label discovery)

**ui/src/services/**
- Purpose: HTTP client for API communication
- Contains: fetch-based API functions
- Key files: `api.ts` (fetchLabels, uploadImage)

**ui/src/types/**
- Purpose: TypeScript type definitions
- Contains: Interfaces for API responses
- Key files: `index.ts` (LabelsResponse, UploadResponse, etc.)

## Key File Locations

**Entry Points:**

- `api/src/main.py`: FastAPI app with lifespan hook (loads model at startup)
- `ui/src/main.tsx`: React entry point (mounts to #root)
- `model/src/train.py`: Training CLI (python -m src.train --s3-bucket ...)
- `model/src/evaluate.py`: Evaluation CLI (python -m src.evaluate --artifact ...)

**Configuration:**

- `api/src/config.py`: Pydantic BaseSettings with S3 bucket, endpoint URL, model path, CORS origins
- `docker-compose.yml`: Service definitions (api, ui, model, localstack); environment variables
- `.env` files: Not committed; referenced by `config.py` via `ENVIRONMENT` env var
- `ui/src/services/api.ts`: API_URL set from Vite env var `import.meta.env.API_URL`

**Core Logic:**

- `api/src/inference.py`: ClassificationModel class (load artifact, predict on bytes)
- `api/src/services/s3.py`: S3Service class (upload training images with timestamp + UUID)
- `api/src/labels.py`: ALL_LABELS_LIST and ALL_LABELS (67 waste categories)
- `model/src/dataset.py`: WasteDataset class (download from S3, create train/val/test splits)
- `model/src/train.py`: train() function (two-phase transfer learning with Mixup)
- `ui/src/components/PhotoCapture.tsx`: State machine with phases (capture, label, uploading, result)

**Testing:**

- `api/tests/test_predict_endpoint.py`: Integration tests for /predict (mocked ClassificationModel)
- `api/tests/test_upload.py`: Integration tests for /upload (mocked S3Service)
- `api/tests/test_inference.py`: Unit tests for ClassificationModel.predict()
- `model/tests/test_train.py`: Unit tests for training loop
- `model/tests/test_dataset.py`: Unit tests for WasteDataset

## Naming Conventions

**Files:**

- Python files: `snake_case.py` (e.g., `inference.py`, `test_predict_endpoint.py`)
- React files: `PascalCase.tsx` (components), `camelCase.ts` (hooks/services)
- Config: `lowercase.json`, `lowercase.toml`, `UPPERCASE.md` (documentation)

**Directories:**

- Python packages: `lowercase/` (e.g., `api/src/`, `model/src/`)
- React components: `Components/` with co-located styles (e.g., `PhotoCapture.tsx`, `PhotoCapture.css`)
- Feature directories: `lowercase/` (e.g., `components/`, `hooks/`, `services/`)

**Functions/Methods:**

- Python: `snake_case()` (e.g., `freeze_backbone()`, `upload_training_image()`)
- React: `camelCase()` or PascalCase for components (e.g., `useImageUpload()`, `PhotoCapture()`)

**Variables:**

- Python: `snake_case` (e.g., `model_artifact_path`, `label_smoothing`)
- TypeScript: `camelCase` (e.g., `imageBase64`, `previewUrl`)

**Types/Classes:**

- Python: `PascalCase` (e.g., `ClassificationModel`, `WasteDataset`, `S3Service`)
- TypeScript: `PascalCase` interfaces (e.g., `LabelsResponse`, `UploadResponse`)

## Where to Add New Code

**New Feature (end-to-end):**
- UI component: Add to `ui/src/components/`
- Hook: Add to `ui/src/hooks/` (if reusable state logic)
- API route: Add to `api/src/main.py` or new `api/src/routes/{feature}.py`
- Tests: Add to `api/tests/test_{feature}.py`

**New Component/Module:**
- React: Create file in `ui/src/components/` with same name
- Python API: Create file in `api/src/` or `api/src/services/`
- Python training: Create file in `model/src/`

**Utilities:**
- React hooks: `ui/src/hooks/{name}.ts`
- React services: `ui/src/services/{name}.ts`
- Python API services: `api/src/services/{name}.py`
- Python training helpers: `model/src/{name}.py`

**Tests:**
- API tests: `api/tests/test_{module}.py` (co-located with tested module)
- Model tests: `model/tests/test_{module}.py`
- UI tests: Would go in `ui/src/` or `ui/__tests__/` (not yet structured)

## Special Directories

**model/artifacts/:**
- Purpose: Store trained model weights
- Generated: Yes (by `python -m src.train`)
- Committed: No (gitignored; models committed to model registry or DVC)
- Contents: `.safetensors` files named `efficientnet_b0_recycling_v{N}.safetensors` with metadata JSON

**model/checkpoints/:**
- Purpose: Store per-epoch training checkpoints
- Generated: Yes (after each training epoch)
- Committed: No (gitignored; only final artifact is kept)
- Contents: `checkpoint_epoch_{NNN}.safetensors`

**localstack-data/:**
- Purpose: Persistent LocalStack S3 data for local development
- Generated: Yes (by LocalStack container)
- Committed: No (gitignored; recreated on each `make init-localstack`)
- Contents: Local S3 bucket state

**ui/dist/:**
- Purpose: Production build artifacts
- Generated: Yes (by `npm run build`)
- Committed: No (generated from source)
- Contents: Minified HTML/JS/CSS ready for Nginx or CDN

**api/.venv/ / model/.venv/:**
- Purpose: Python virtual environments
- Generated: Yes (by `make setup` or `pip install`)
- Committed: No (gitignored)
- Contents: Installed Python packages

---

*Structure analysis: 2026-02-26*
