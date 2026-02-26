# Quickstart: Waste Item Image Classifier

**Feature**: `001-waste-item-classifier`
**Date**: 2026-02-25

---

## Prerequisites

- Docker and Docker Compose installed
- AWS credentials configured (or LocalStack running for local development)
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

---

## 1. Train a Model

Training downloads labeled images from S3 and produces a `.safetensors` artifact.

```bash
# From repo root — runs training inside the model Docker container
docker-compose run model uv run python -m model.src.train \
  --s3-bucket recycling-buddy-training \
  --output-dir model/artifacts/ \
  --epochs 30 \
  --seed 42
```

Training runs in two phases:
- **Phase 1** (~10 epochs): Only the 67-class classifier head is trained; the backbone is frozen.
- **Phase 2** (~20 epochs): All layers are fine-tuned with differential learning rates.

Expected output:
```
[Phase 1] Epoch 10/10  loss=1.23  val_acc=0.61
[Phase 2] Epoch 30/30  loss=0.42  val_acc=0.88
Artifact saved: model/artifacts/efficientnet_b0_recycling_v1.safetensors (20.5 MB)
```

To resume a stopped training run:
```bash
docker-compose run model uv run python -m model.src.train \
  --s3-bucket recycling-buddy-training \
  --output-dir model/artifacts/ \
  --resume model/artifacts/checkpoint_epoch_15.safetensors
```

---

## 2. Evaluate a Trained Model

```bash
docker-compose run model uv run python -m model.src.evaluate \
  --artifact model/artifacts/efficientnet_b0_recycling_v1.safetensors \
  --s3-bucket recycling-buddy-training \
  --split test
```

Expected output (JSON to stdout):
```json
{
  "overall_top1_accuracy": 0.87,
  "overall_top3_accuracy": 0.96,
  "per_category": {
    "cardboard": 0.94,
    "plastic-bags-soft-plastic": 0.71,
    ...
  },
  "confused_pairs": [
    ["plastic-lined-cardboard", "cardboard", 12],
    ...
  ]
}
```

A category passes the deployment gate if `per_category[label] >= 0.60` (SC-003).

---

## 3. Configure the API to Use the Artifact

Set the model artifact path in the API's environment config:

```bash
# config/dev.env  (gitignored)
MODEL_ARTIFACT_PATH=/app/model/artifacts/efficientnet_b0_recycling_v1.safetensors
```

The path `/app/model/...` resolves inside the API container because `./model` is mounted at `/app/model` in `docker-compose.yml`.

---

## 4. Start the Full Stack

```bash
docker-compose up --build
```

This starts:
- **LocalStack** (S3 mock) at `localhost:4566`
- **API** (FastAPI) at `localhost:8000` — loads the model at startup
- **UI** (React/Vite) at `localhost:5173`

Verify the API loaded the model:
```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"0.1.0"}
```

---

## 5. Test Inference

```bash
# Classify a waste item image
curl -X POST http://localhost:8000/predict \
  -F "file=@/path/to/cardboard-box.jpg"
```

Expected response:
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

---

## 6. Run Tests

```bash
# API tests (includes inference integration tests)
cd api && uv run pytest

# Model tests (training pipeline, dataset loading, evaluation)
cd model && uv run pytest
```

All tests must pass before merging. See the constitution for test discipline requirements.
