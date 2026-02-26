# Contract: Inference API

**Feature**: `001-waste-item-classifier`
**Date**: 2026-02-25

This document defines the contracts exposed by the classifier feature across two boundaries:

1. **Internal Python contract** — the `ClassificationModel` interface consumed by `api/src/main.py`
2. **HTTP contract** — the `/predict` endpoint consumed by the UI and external clients

---

## 1. Internal Python Contract: `ClassificationModel`

**Module**: `api/src/inference.py`

This class is the single internal boundary between the FastAPI route layer and the PyTorch model. It is the only component that imports `torch` or `torchvision` within the API.

### Class: `ClassificationModel`

```python
class ClassificationModel:
    """
    Wraps a PyTorch EfficientNet-B0 model for thread-safe CPU inference.
    Loaded once at application startup via the FastAPI lifespan event.
    Shared safely across concurrent requests — model.eval() is set once
    at construction; no shared mutable state during forward passes.
    """

    @classmethod
    def from_artifact(cls, artifact_path: str) -> "ClassificationModel":
        """
        Load a trained model from a safetensors artifact file.

        Sets torch.set_num_threads(4) and torch.set_num_interop_threads(1)
        before any tensor operations. Must be called before the first request
        is accepted (i.e., inside the FastAPI lifespan context manager).

        Args:
            artifact_path: Absolute path to a .safetensors model artifact file.

        Returns:
            ClassificationModel ready for concurrent inference.

        Raises:
            FileNotFoundError: If artifact_path does not exist.
            ValueError: If the artifact is incompatible with the expected
                        model architecture (67 output classes, EfficientNet-B0).
        """

    def predict(self, image_bytes: bytes) -> "ClassificationResult":
        """
        Classify a waste item image.

        Thread-safe: may be called concurrently from multiple threads.
        Must be called via run_in_threadpool() from async FastAPI routes
        to avoid blocking the event loop.

        Args:
            image_bytes: Raw image bytes in JPEG, PNG, or WEBP format.
                         The bytes are not stored or written anywhere.

        Returns:
            ClassificationResult containing the top prediction and top-3
            alternatives with confidence scores.

        Raises:
            ValueError: If image_bytes cannot be decoded as a valid image.
        """
```

### Value Objects

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CategoryPrediction:
    label: str    # member of api/src/labels.ALL_LABELS_LIST
    confidence: float  # softmax probability [0.0, 1.0]

@dataclass(frozen=True)
class ClassificationResult:
    top_prediction: CategoryPrediction
    alternatives: list[CategoryPrediction]  # len == 3, index 0 == top_prediction
```

### Usage in `api/src/main.py`

```python
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = ClassificationModel.from_artifact(settings.model_artifact_path)
    yield
    # No explicit cleanup needed for read-only model

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: Request, file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    image_bytes = await file.read()
    result = await run_in_threadpool(request.app.state.model.predict, image_bytes)
    return PredictionResponse(
        label=result.top_prediction.label,
        confidence=result.top_prediction.confidence,
        categories=[{p.label: p.confidence} for p in result.alternatives],
    )
```

### Constraints

- `ClassificationModel` MUST NOT be imported or instantiated at module level — only inside the `lifespan` context manager
- `predict()` MUST NOT store `image_bytes` or any derivative of it after returning
- `predict()` MUST be called within `torch.inference_mode()` internally
- `from_artifact()` MUST call `model.eval()` and never allow it to be toggled back to training mode

---

## 2. HTTP Contract: `POST /predict`

This endpoint already exists in `api/src/main.py` with a stub implementation. This contract defines the completed behaviour.

### Request

```
POST /predict
Content-Type: multipart/form-data
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `file` | File upload | Yes | JPEG, PNG, or WEBP image |

**Content-type validation**: The API validates `file.content_type` starts with `image/` before reading bytes.

### Response: 200 OK

```json
{
  "label": "cardboard",
  "confidence": 0.923,
  "categories": [
    {"cardboard": 0.923},
    {"plastic-lined-cardboard": 0.041},
    {"paper": 0.018}
  ]
}
```

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `label` | `string` | member of ALL_LABELS (67 values) | Top-1 predicted category |
| `confidence` | `number` | 0.0 ≤ value ≤ 1.0 | Softmax probability for top-1 |
| `categories` | `array` | len == 3 | Top-3 label-confidence pairs, descending order |

**Note**: The `categories` field shape (`list[dict[str, float]]`) matches the existing `PredictionResponse` Pydantic model in `main.py`. No schema changes required.

### Error Responses

| Status | Condition | Body |
|--------|-----------|------|
| 400 | `file` missing or not multipart | `{"detail": "File must be an image"}` |
| 400 | File cannot be decoded as a valid image | `{"detail": "Invalid image format"}` |
| 500 | Inference failure (unexpected) | `{"detail": "Internal server error"}` |

### Side Effects

- A structured JSON log line is emitted for every successful prediction (FR-013):
  ```json
  {"event": "prediction", "timestamp": "...", "predicted_label": "cardboard", "confidence": 0.923}
  ```
- The submitted image bytes are NOT stored anywhere after the response is returned.

---

## 3. Training Pipeline Contract

**Module**: `model/src/train.py`

The training pipeline is invoked as a script (not via the API). It is the only component that writes to the `model/artifacts/` directory.

### CLI Interface

```
uv run python -m model.src.train \
  --s3-bucket recycling-buddy-training \
  --output-dir model/artifacts/ \
  --epochs 30 \
  --seed 42
```

| Argument | Required | Default | Notes |
|----------|----------|---------|-------|
| `--s3-bucket` | Yes | — | S3 bucket containing labeled training images |
| `--output-dir` | No | `model/artifacts/` | Where to write the .safetensors artifact |
| `--epochs` | No | 30 | Total training epochs (phase 1 + phase 2) |
| `--seed` | No | 42 | Random seed for reproducibility |
| `--resume` | No | None | Path to a prior checkpoint to resume from |

### Outputs

1. A `.safetensors` model artifact in `--output-dir`
2. A `training_run_{timestamp}.json` metadata file recording: epoch count, final val accuracy, per-category val accuracy, random seed

### Evaluation Pipeline Contract

**Module**: `model/src/evaluate.py`

```
uv run python -m model.src.evaluate \
  --artifact model/artifacts/efficientnet_b0_recycling_v1.safetensors \
  --s3-bucket recycling-buddy-training \
  --split test
```

Outputs a JSON report to stdout with: overall top-1 accuracy, overall top-3 accuracy, per-category top-1 accuracy, confusion matrix of the top-10 most confused pairs.
