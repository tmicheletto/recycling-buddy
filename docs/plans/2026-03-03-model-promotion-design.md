# Design: S3-based Model Promotion

**Date:** 2026-03-03
**Status:** Approved

## Problem

The model training pipeline produces a `.safetensors` artifact on the local filesystem. There is no mechanism to get this artifact into the production ECS container — the API Docker image only includes the Python source, not the artifact. Production deployments start in degraded state and `/predict` returns 503.

## Solution

Add a `recbuddy.promote` CLI that uploads a trained artifact to S3. Extend `MODEL_ARTIFACT_PATH` to accept an `s3://` URI so the API can download the artifact at startup when running in production.

## Architecture

### Promotion (model pipeline)

```
train → evaluate → recbuddy.promote → S3
                                        ├── artifacts/efficientnet_b0_recycling_latest.safetensors
                                        ├── artifacts/efficientnet_b0_recycling_v{N}.safetensors
                                        └── artifacts/latest.json
```

### Consumption (API)

```
ECS container starts
  → lazy-load triggered on first /predict
  → MODEL_ARTIFACT_PATH=s3://recycling-buddy-data/artifacts/efficientnet_b0_recycling_latest.safetensors
  → parse s3:// URI → download to /tmp/model.safetensors
  → ClassificationModel.from_artifact(/tmp/model.safetensors)
```

### Dev workflow (unchanged)

`MODEL_ARTIFACT_PATH` is a local path (volume-mounted). The s3:// branch is never triggered.

## Components

### 1. `model/recbuddy/promote.py` (new)

CLI module for promoting a trained artifact to S3.

```
uv run python -m recbuddy.promote \
    --artifact artifacts/efficientnet_b0_recycling_v1.safetensors \
    --s3-bucket recycling-buddy-data
```

Behaviour:
- Uploads artifact to `artifacts/efficientnet_b0_recycling_latest.safetensors` (stable key used by the API)
- Also uploads to `artifacts/efficientnet_b0_recycling_v{N}.safetensors` (versioned, derived from local filename)
- Writes `artifacts/latest.json` with `{"version": "v1", "artifact_key": "...", "promoted_at": "..."}`
- Uses boto3 with the same auth pattern as `recbuddy.dataset`
- Optional `--s3-endpoint-url` for LocalStack

### 2. `api/app/services/s3.py`

Add `download_artifact(bucket, s3_key, local_path)` method using `client.download_file`.

### 3. `api/app/main.py`

In the lazy-load block, before calling `ClassificationModel.from_artifact`:

- If `settings.model_artifact_path` starts with `s3://`, parse bucket and key
- Download to `/tmp/model.safetensors` (inside `run_in_threadpool`)
- Load from the local temp path

Local path behaviour is unchanged.

### 4. `api/task-definition.json`

Add one environment variable:

```json
{"name": "MODEL_ARTIFACT_PATH", "value": "s3://recycling-buddy-data/artifacts/efficientnet_b0_recycling_latest.safetensors"}
```

### 5. `model/Makefile` (new)

Targets for the full model workflow:

```makefile
ARTIFACT ?= artifacts/efficientnet_b0_recycling_v1.safetensors
S3_BUCKET ?= recycling-buddy-data

train:     # uv run python -m recbuddy.train
evaluate:  # uv run python -m recbuddy.evaluate
promote:   # uv run python -m recbuddy.promote
test:      # uv run pytest
```

## Workflow

```bash
# From model/
make train
make evaluate ARTIFACT=artifacts/efficientnet_b0_recycling_v1.safetensors
make promote ARTIFACT=artifacts/efficientnet_b0_recycling_v1.safetensors

# Next ECS deploy → API downloads from s3:// URI → /predict works
```

## Testing

- `model/tests/test_promote.py` — mock boto3 client; verify versioned upload, latest upload, and manifest write
- `api/tests/test_s3.py` — add test for `download_artifact` (mock `download_file`)
- `api/tests/test_main.py` — add test for s3:// lazy-load branch (mock `Path.exists` → False, mock s3_service, verify download called before load)

## Assumptions

- The ECS task role (`recycling-buddy-api`) has `s3:GetObject` on `recycling-buddy-data/artifacts/*`
- The artifact is ~20MB (EfficientNet-B0 safetensors), so the download adds ~1–2s to first request cold start — acceptable for this project
- Dev docker-compose is unchanged: `MODEL_ARTIFACT_PATH` remains a local path
