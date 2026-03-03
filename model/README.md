# Model Component

EfficientNet-B0 image classifier for 67 household waste categories.

## Overview

This component handles:
- Training the classifier on labeled images stored in S3
- Evaluating a trained model artifact against a held-out test split
- Producing `.safetensors` model artifacts consumed by the API service

## Directory Structure

```
model/
├── src/
│   ├── __init__.py
│   ├── dataset.py       # WasteDataset: S3 download + train/val/test splits
│   ├── transforms.py    # inference_transform() and training_transform() pipelines
│   ├── train.py         # Two-phase training + CLI entry point
│   └── evaluate.py      # Metrics computation + CLI entry point
├── tests/               # Unit tests (pytest)
├── artifacts/           # Trained model artifacts (gitignored)
├── checkpoints/         # Per-epoch safetensors checkpoints (gitignored)
└── pyproject.toml       # Dependencies and tool config (managed by uv)
```

## Setup

```bash
cd model
uv sync
```

## Training

Run via Docker Compose (recommended):

```bash
docker-compose run model uv run python -m src.train \
    --s3-bucket recycling-buddy-training \
    --output-dir model/artifacts/ \
    --epochs 30 \
    --seed 42
```

Or locally against LocalStack:

```bash
cd model
AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
uv run python -m src.train \
    --s3-bucket recycling-buddy-training \
    --s3-endpoint-url http://localhost:4566 \
    --output-dir artifacts/ \
    --epochs 30
```

The training pipeline runs in two phases:
- **Phase 1** (5 epochs): Backbone frozen, head trained with AdamW lr=1e-3
- **Phase 2** (25 epochs): Full fine-tune, backbone lr=1e-5, head lr=1e-4, cosine schedule, Mixup

Checkpoints are saved to `model/checkpoints/` after each epoch. The final artifact is saved to `model/artifacts/efficientnet_b0_recycling_v{N}.safetensors`.

To resume from a checkpoint:

```bash
uv run python -m src.train \
    --s3-bucket recycling-buddy-training \
    --resume model/checkpoints/checkpoint_epoch_010.safetensors \
    --output-dir artifacts/ \
    --epochs 30
```

## Evaluation

```bash
cd model
uv run python -m src.evaluate \
    --artifact artifacts/efficientnet_b0_recycling_v1.safetensors \
    --s3-bucket recycling-buddy-training \
    --split test
```

Outputs a JSON report to stdout:

```json
{
  "overall_top1_accuracy": 0.872,
  "overall_top3_accuracy": 0.961,
  "per_category": {
    "cardboard": 0.91,
    "plastic-bottles-containers": 0.85,
    ...
  },
  "confused_pairs": [
    ["glass-bottles-jars", "plastic-bottles-containers", 3],
    ...
  ]
}
```

Categories with top-1 accuracy below 60% are flagged to stderr.

## Promotion

After evaluating a satisfactory artifact, promote it to S3:

```bash
cd model
make promote ARTIFACT=artifacts/efficientnet_b0_recycling_v1.safetensors
```

Or directly:

```bash
uv run python -m recbuddy.promote \
    --artifact artifacts/efficientnet_b0_recycling_v1.safetensors \
    --s3-bucket recycling-buddy-data
```

This uploads the artifact to two S3 keys:
- `artifacts/efficientnet_b0_recycling_latest.safetensors` — the stable key the API uses
- `artifacts/efficientnet_b0_recycling_v{N}.safetensors` — versioned copy for history

It also writes `artifacts/latest.json` with version and timestamp metadata.

The next ECS deploy will pick up the new artifact automatically on first `/predict` request.

## Tests

```bash
cd model
uv run pytest
```

## Model Architecture

- **Backbone**: EfficientNet-B0 (ImageNet pretrained, `EfficientNet_B0_Weights.IMAGENET1K_V1`)
- **Head**: `nn.Linear(1280, 67)` replacing the default classifier
- **Input**: 224×224 RGB, ImageNet normalisation
- **Output**: 67-class softmax over waste item categories
- **Artifact format**: safetensors state dict (≤100 MB)

## Artifact Path

The API reads the trained model from the path set by `MODEL_ARTIFACT_PATH` in the environment (default: `model/artifacts/efficientnet_b0_recycling_v1.safetensors`).
