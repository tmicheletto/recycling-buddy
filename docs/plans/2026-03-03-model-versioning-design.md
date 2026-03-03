# Model Versioning Design

## Goal

Add traceability and rollback capability to model artifacts. Every deployed model version should be identifiable, and rolling back to a previous version should be a config change + redeploy.

## S3 Layout

```
s3://recycling-buddy-data/
  artifacts/
    0.1.0/
      model.safetensors
      manifest.json
    0.2.0/
      model.safetensors
      manifest.json
```

Each version is a self-contained directory. No `_latest` alias key. The version comes from `model/pyproject.toml` (semver).

## Manifest Schema

Each `artifacts/{version}/manifest.json`:

```json
{
  "version": "0.2.0",
  "artifact_key": "artifacts/0.2.0/model.safetensors",
  "training": {
    "epochs": 30,
    "val_accuracy": 0.9142,
    "seed": 42,
    "num_classes": 67
  },
  "promotion": {
    "promoted_at": "2026-03-03T12:00:00Z",
    "promoted_by": "tim",
    "git_sha": "40c62ef",
    "replaced_version": "0.1.0"
  }
}
```

## Promotion Flow

`promote.py` changes:

- Read version from `model/pyproject.toml` instead of auto-incrementing
- Upload artifact to `artifacts/{version}/model.safetensors`
- Build manifest from training sidecar metadata + promotion context (timestamp, git SHA, promoter, replaced version)
- Upload manifest to `artifacts/{version}/manifest.json`
- Error if `artifacts/{version}/` already exists in S3 (prevents accidental overwrites — bump version in pyproject.toml first)
- Print the new S3 URI for the operator to update config
- Remove `_latest` key upload and top-level `latest.json` manifest

## API Changes

Minimal:

- `_resolve_artifact_path()` in `main.py` unchanged — already handles S3 URIs
- `MODEL_ARTIFACT_PATH` in `task-definition.json` changes to versioned path: `s3://recycling-buddy-data/artifacts/0.1.0/model.safetensors`
- `config.py` default changes to `model/artifacts/model.safetensors`
- Log the loaded model version at startup
- `docker-compose.yml` env var updated to match

No changes to the predict endpoint response. No manifest reading at runtime.

## Training Pipeline Changes

- `train.py` outputs `model.safetensors` (not `efficientnet_b0_recycling_v{N}.safetensors`)
- `_next_version()` auto-increment logic removed
- Training metadata sidecar continues to be emitted as-is

## Local Dev Workflow

1. Bump version in `model/pyproject.toml`
2. `make train` → outputs `model/artifacts/model.safetensors`
3. `make promote` → uploads to `artifacts/{version}/model.safetensors` + manifest
4. Update `MODEL_ARTIFACT_PATH` in `task-definition.json` to `s3://recycling-buddy-data/artifacts/{version}/model.safetensors`
5. Redeploy

Rollback: change step 4 to a previous version, redeploy.

## Non-Goals

- A/B testing or running multiple versions simultaneously
- API exposing model version in predict response
- Global manifest listing all versions (just use S3 listing)
- Serving-time metadata tracking
