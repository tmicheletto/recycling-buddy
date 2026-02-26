# Implementation Plan: Waste Item Image Classifier

**Branch**: `001-waste-item-classifier` | **Date**: 2026-02-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-waste-item-classifier/spec.md`

## Summary

Build a 67-class image classifier for household waste items using PyTorch + EfficientNet-B0 with transfer learning. The model is trained offline on a labeled S3 dataset and served as an in-process Python callable within the existing FastAPI application. The `POST /predict` endpoint (currently stubbed) is completed to load the trained artifact at startup and call the classifier on each request via a thread pool. A separate training pipeline and evaluation pipeline are provided as runnable scripts in the `model/` component.

## Technical Context

**Language/Version**: Python 3.11 (Dockerfile target; `model/` and `api/` both)
**Primary Dependencies**: PyTorch (CPU-only), torchvision, safetensors, Pillow (inference); FastAPI, Pydantic v2, Starlette (API); boto3 (S3 dataset download)
**Storage**: S3 (training images, read-only during training); `model/artifacts/` (model weights, local filesystem, gitignored)
**Testing**: `uv run pytest`; `anyio` for async tests
**Target Platform**: Linux (Docker container, CPU-only — no GPU assumed)
**Project Type**: ML model (training + evaluation scripts) + web-service (in-process inference)
**Performance Goals**: Top-1 accuracy ≥ 85% on test set; inference latency < 500 ms per image on CPU; model artifact ≤ 100 MB
**Constraints**: No GPU; CPU-only inference; in-process (not a separate HTTP service); images discarded after inference; up to 10 concurrent inference requests
**Scale/Scope**: 67 categories; 50–500 labeled images per category (~3,350–33,500 total); 1 model artifact in production at any time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Type Safety | PASS | `ClassificationModel.predict()` returns typed dataclasses; `PredictionResponse` is Pydantic v2; all new Python functions carry type hints |
| II. TDD | PASS (committed) | Tests written alongside each module: `test_classifier.py`, `test_train.py`, `test_evaluate.py`, `test_inference.py` |
| III. YAGNI | PASS | Single-image inference only; no batch API; no online retraining; no separate model microservice |
| IV. Docker-First | **VIOLATION** | `model/Dockerfile` uses `pip install` — must be rewritten to use `uv` with multi-stage build |
| V. Observability | PASS | FR-013: structured JSON prediction log; API input validation already present at `/predict` |

**VIOLATION resolution plan** (Principle IV):
`model/Dockerfile` will be rewritten as a multi-stage uv build. The violation is not a blocker for development but MUST be resolved before the first Docker-based test run.

### Post-Phase 1 Re-check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Type Safety | PASS | `ClassificationModel`, `CategoryPrediction`, `ClassificationResult` all typed; `from_artifact()` and `predict()` carry full type signatures |
| II. TDD | PASS | Contract defines testable boundaries; unit tests for model loading, inference pipeline, and prediction response shape |
| III. YAGNI | PASS | `api/src/inference.py` added (one new module); no additional abstractions introduced |
| IV. Docker-First | PASS (planned fix) | `model/Dockerfile` rewrite included in tasks |
| V. Observability | PASS | Prediction log entry shape defined in data-model; emitted as structured JSON per constitution Principle V |

**Spec vs Constitution discrepancy** — constitution targets are binding:

| Metric | Spec | Constitution | Used in plan |
|--------|------|--------------|--------------|
| Accuracy | >80% top-1 | >85% val | **85%** |
| Latency | <2 sec | <500 ms | **500 ms** |
| Model size | (not stated) | <100 MB | **100 MB** |

## Project Structure

### Documentation (this feature)

```text
specs/001-waste-item-classifier/
├── plan.md              ← this file
├── research.md          ← Phase 0: framework, backbone, training, serialization decisions
├── data-model.md        ← Phase 1: entities and relationships
├── quickstart.md        ← Phase 1: how to train, evaluate, and run locally
├── contracts/
│   └── inference-api.md ← Phase 1: ClassificationModel interface + HTTP /predict contract
└── tasks.md             ← Phase 2 output (/speckit.tasks command)
```

### Source Code

```text
model/
├── pyproject.toml           # NEW — uv-managed package (was missing)
├── Dockerfile               # FIX — rewrite to use uv + multi-stage build
├── src/
│   ├── __init__.py          # existing
│   ├── dataset.py           # NEW — S3 download, train/val/test split, ImageFolder setup
│   ├── train.py             # NEW — two-phase EfficientNet-B0 fine-tuning pipeline
│   ├── evaluate.py          # NEW — per-category accuracy, top-3 acc, confusion matrix
│   └── transforms.py        # NEW — training and inference torchvision.transforms.v2 pipelines
├── tests/
│   ├── __init__.py          # NEW
│   ├── test_dataset.py      # NEW
│   ├── test_train.py        # NEW
│   └── test_evaluate.py     # NEW
├── artifacts/               # gitignored — safetensors model files
└── checkpoints/             # gitignored — training epoch checkpoints

api/src/
├── inference.py             # NEW — ClassificationModel (loads artifact, runs predict())
├── main.py                  # UPDATE — add lifespan event, complete /predict stub
├── config.py                # UPDATE — add model_artifact_path setting
├── labels.py                # existing (unchanged)
└── services/
    └── s3.py                # existing (unchanged)

api/tests/
├── test_inference.py        # NEW — unit tests for ClassificationModel
└── test_predict_endpoint.py # NEW — integration tests for POST /predict
```

**Structure Decision**: The inference module lives in `api/src/` (not `model/src/`) because it is the API's responsibility to load and serve the model. The `model/` component owns only training artifacts and offline pipeline scripts. The two components communicate exclusively through the `.safetensors` artifact file, mounted at `/app/model/artifacts/` in the API container via docker-compose volume mount.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| `model/Dockerfile` currently uses `pip` | Legacy placeholder; not yet used for training | N/A — this is a fix, not a justified violation. Will be corrected. |
