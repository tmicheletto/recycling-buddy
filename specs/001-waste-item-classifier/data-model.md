# Data Model: Waste Item Image Classifier

**Phase**: 1 — Design
**Feature**: `001-waste-item-classifier`
**Date**: 2026-02-25

---

## Entities

### 1. WasteImage (ephemeral, never persisted)

Represents the raw image submitted by the caller for classification. Exists only for the duration of a single inference call.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `raw_bytes` | `bytes` | len > 0 | JPEG, PNG, or WEBP bytes |
| `format` | `str` | one of `jpeg`, `png`, `webp` | Derived from magic bytes or content-type header |

**Lifecycle**: Created at API request boundary → passed to classifier → discarded after prediction returned. Not written to any storage medium (FR-012).

**Validation rules**:
- Must be decodable as a valid image by Pillow
- Format must be JPEG, PNG, or WEBP (validated at API boundary before classification)

---

### 2. CategoryPrediction (value object)

A single label-confidence pair. Used both for the top prediction and for the top-3 alternatives list.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `label` | `str` | member of `ALL_LABELS` (67 values) | Drawn exclusively from `api/src/labels.py` |
| `confidence` | `float` | 0.0 ≤ value ≤ 1.0 | Softmax probability for this class |

---

### 3. ClassificationResult (value object, returned by inference callable)

The output of the `classify()` function. Contains the top prediction and top-3 alternatives ordered by confidence descending.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `top_prediction` | `CategoryPrediction` | required | Highest-confidence prediction |
| `alternatives` | `list[CategoryPrediction]` | len == 3 | Top 3 by confidence descending, includes `top_prediction` at index 0 |

**Invariants**:
- `alternatives[0].label == top_prediction.label`
- `alternatives[0].confidence == top_prediction.confidence`
- `sum(p.confidence for p in alternatives)` ≤ 1.0 (probabilities from a softmax distribution)
- All labels in `alternatives` are distinct

---

### 4. PredictionLogEntry (persisted log record)

Recorded for every inference call. Contains no image data (FR-012/FR-013).

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `timestamp` | `datetime` | UTC, ISO-8601 | When inference completed |
| `predicted_label` | `str` | member of `ALL_LABELS` | The top-1 predicted label |
| `confidence` | `float` | 0.0 ≤ value ≤ 1.0 | Confidence of top-1 prediction |

**Storage**: Emitted as a structured JSON log line by the API's logging system. Not stored in a database at this stage — log aggregation is out of scope.

**Log format** (JSON-compatible, per constitution Principle V):
```json
{
  "event": "prediction",
  "timestamp": "2026-02-25T04:00:00Z",
  "predicted_label": "cardboard",
  "confidence": 0.923
}
```

---

### 5. WasteCategory (immutable domain constant)

One of the 67 predefined waste item categories. Defined in `api/src/labels.py` and treated as immutable at runtime — additions or removals require a full model retrain.

| Field | Type | Notes |
|-------|------|-------|
| `label` | `str` | S3-safe string: lowercase letters, digits, hyphens |
| `display_name` | `str` | Human-readable, derived by replacing `-` with spaces and title-casing |

**Canonical source**: `api/src/labels.py::ALL_LABELS_LIST` (67 entries). No other definition is authoritative.

---

### 6. LabeledDataset (training artifact, not a runtime entity)

A collection of images on S3 partitioned into train, validation, and test splits.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `s3_prefix` | `str` | valid S3 key prefix | e.g. `cardboard/` |
| `split` | `str` | one of `train`, `val`, `test` | Determined at dataset preparation time |
| `category` | `WasteCategory` | required | The ground-truth label for all images under this prefix |
| `image_count` | `int` | 50–500 per category per dataset | Approximate; actual counts vary by category |

**S3 key structure**: `<label>/<filename>.<ext>` — matches the existing S3 upload structure in `api/src/main.py`.

**Split ratios** (standard for moderate datasets):
- Train: 70%
- Validation: 15%
- Test: 15%

---

### 7. ModelArtifact (training output, deployment input)

A serialised, versioned snapshot of a trained EfficientNet-B0 model with its 67-class head.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `filename` | `str` | pattern: `efficientnet_b0_recycling_v{N}.safetensors` | N is a monotonically increasing integer |
| `version` | `int` | ≥ 1 | Incremented on each successful training run |
| `created_at` | `datetime` | UTC | Training completion timestamp |
| `val_accuracy` | `float` | 0.0–1.0 | Top-1 accuracy on validation split at training completion |
| `num_classes` | `int` | == 67 | Fixed; must match `len(ALL_LABELS_LIST)` |

**Storage path**: `model/artifacts/` (gitignored). Loading path configured via `MODEL_ARTIFACT_PATH` environment variable.

**Size constraint**: ≤ 100 MB (EfficientNet-B0 state dict in safetensors format is ~20.5 MB).

---

## Entity Relationships

```
WasteImage ──(input to)──► classifier.classify() ──(returns)──► ClassificationResult
                                                                        │
ClassificationResult ──(contains)──► CategoryPrediction (×3)
                                              │
                                      uses label from ──► WasteCategory (×67)

ClassificationResult ──(logged as)──► PredictionLogEntry (no image data)

LabeledDataset ──(used by)──► training pipeline ──(produces)──► ModelArtifact
ModelArtifact ──(loaded by)──► classifier.classify()
```

---

## State Transitions

### ModelArtifact lifecycle

```
[training run completes]
        │
        ▼
  artifact saved to
  model/artifacts/
        │
        ▼
  [manual promotion]
        │
        ▼
  MODEL_ARTIFACT_PATH env
  var updated to new file
        │
        ▼
  API restarts and loads
  new artifact at startup
```

No automatic model promotion — a human reviews validation accuracy before updating the deployment artifact path.
