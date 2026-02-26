# Codebase Concerns

**Analysis Date:** 2026-02-26

## Error Handling

**Broad exception catching in API:**
- Issue: Multiple endpoints catch `Exception` generically, logging only generic error messages and obscuring root causes
- Files: `api/src/main.py` (lines 147, 218, 230)
- Impact: Difficult debugging in production; operators cannot distinguish between image decode failures, S3 errors, and unexpected runtime errors
- Fix approach: Catch specific exception types (`ValueError`, `ClientError`, etc.) separately; log meaningful context (error type, failed operation, state)

**Example fragile pattern in `api/src/main.py` line 230:**
```python
except Exception as e:
    logger.error(f"Upload error: {str(e)}")  # No exception type, context lost
    raise HTTPException(status_code=500, detail="Failed to upload image")
```

Should differentiate between:
- `ValueError` (invalid base64)
- `botocore.exceptions.ClientError` (S3 unavailable, permissions, bucket missing)
- `ClientError` with specific error codes (rate limiting, quota)

## Performance Bottlenecks

**Single-threaded data loading:**
- Problem: `num_workers=0` in both train and validation DataLoaders
- Files: `model/src/train.py` (lines 255, 257)
- Cause: This disables multiprocess data loading, causing CPU pipeline to wait on image decode operations sequentially
- Improvement path: Set `num_workers=4` or `num_workers=cpu_count() // 2`; validate on target hardware that fork/spawn behavior works correctly with safetensors
- Risk: May introduce compatibility issues on some systems if not tested

**No prefetch in training loop:**
- Problem: ImageFolder loads from disk per-batch; no prefetching/caching of next batch while compute happens
- Files: `model/src/train.py` (lines 254-257)
- Impact: GPU/CPU idle time waiting for I/O during training
- Improvement: Use `DataLoader(prefetch_factor=2)` and/or `persistent_workers=True` once `num_workers > 0`

## Scaling Limits

**Fixed model artifact path in config:**
- Risk: Configuration hardcodes `efficientnet_b0_recycling_v1.safetensors` as default artifact path
- Files: `api/src/config.py` (line 17-19)
- Current capacity: Only supports one model version at a time; zero-downtime model updates require manual config change and app restart
- Scaling path: (1) Allow `MODEL_ARTIFACT_PATH` env var override (already does), (2) implement model registry/versioning service to support A/B testing, canary deployments
- Workaround: Override via environment variable; container orchestration can manage config updates

**DataLoader batch size hardcoded to 32:**
- Problem: Training assumes batch_size=32 works on available hardware; not parameterized for different environments
- Files: `model/src/train.py` (line 197)
- Impact: Training fails (OOM or underutilization) if run on lower/higher-memory systems without manual edit
- Improvement path: Make batch size environment-aware or auto-detect; provide guidance in Makefile

**67 hard-coded class count across codebase:**
- Risk: The `num_classes=67` default is duplicated in multiple places
- Files: `model/src/train.py` (line 43), `model/src/evaluate.py` (line 31), `api/src/inference.py` (line 34)
- Impact: Adding a new waste category requires changes in 3+ files; easy to miss and cause shape mismatches
- Improvement path: Derive `num_classes` from `ALL_LABELS_LIST` length or load from artifact metadata; assert consistency at runtime

## Fragile Areas

**Image format detection via magic bytes only:**
- Files: `api/src/main.py` (line 187-202), `api/src/services/s3.py` (line 74-87)
- Why fragile: Only checks first 3-4 bytes; does not validate image headers are valid or complete; corrupted/truncated images may pass
- Safe modification: Use `PIL.Image.verify()` after decode attempt; catch `Image.UnidentifiedImageError` properly
- Test coverage: `api/tests/test_predict_endpoint.py` tests with valid JPEG/PNG but not corrupted/truncated edge cases

**Transform pipeline and training dataset mismatch:**
- Problem: `get_splits()` loads full dataset with `inference_transform()`, then splits, then replaces training dataset with new ImageFolder using `training_transform()`
- Files: `model/src/dataset.py` (lines 100-123)
- Why fragile: The train subset is constructed via `Subset` index reference, then `.dataset` is replaced in-place; if `random_split()` caches references, modifications may not propagate
- Safe modification: Create a `TrainingSubset` wrapper class that applies augmentation inside `__getitem__()` rather than replacing `.dataset`

**Model.eval() permanently set, never toggled:**
- Files: `api/src/inference.py` (line 128)
- Why fragile: Comment states "Disable dropout / BatchNorm training mode; never toggled back" — correct for inference but code lacks assertion/guard against accidental re-enable
- Safe modification: Add `assert not model.training` before inference or in unit test

## Test Coverage Gaps

**No model artifact existence validation in integration tests:**
- What's not tested: Behavior when `MODEL_ARTIFACT_PATH` points to missing file (FileNotFoundError path)
- Files: `api/src/inference.py` (lines 115-119), `api/tests/test_predict_endpoint.py`
- Risk: App startup could fail silently or with poor error message in production if artifact is deleted
- Priority: Medium — guards against deployment misconfiguration

**No S3 connectivity tests:**
- What's not tested: Behavior when S3 bucket is unreachable, credentials invalid, or bucket doesn't exist
- Files: `api/src/services/s3.py`, `model/src/dataset.py`
- Risk: Training fails mid-run with generic "Failed to download" message; upload endpoint returns 500 without useful context
- Priority: Medium — critical path for training pipeline

**No concurrent request handling tests:**
- What's not tested: Multiple simultaneous `/predict` requests; thread safety of model under realistic load
- Files: `api/src/inference.py`, `api/tests/test_predict_endpoint.py`
- Risk: Model is thread-safe in design but no integration test confirms; concurrent requests may reveal memory leaks or race conditions
- Priority: Low in dev; High before production deployment

**Base64 overflow not tested:**
- What's not tested: `/upload` endpoint with extremely large base64 payloads (multi-GB strings)
- Files: `api/src/main.py` (line 217)
- Risk: `base64.b64decode()` may consume unbounded memory, DOS vector
- Priority: Medium — should add payload size limit

## Dependencies at Risk

**No version pinning for critical packages:**
- Risk: `Dockerfile` and requirements use loose version pins (implicit `latest` or `~=` ranges)
- Files: `api/requirements.txt`, `model/requirements.txt` (not examined but inferred from Makefile/setup)
- Impact: Dependencies may break due to major version updates; no reproducible builds
- Migration plan: Pin all transitive dependencies via `uv.lock` file (or `pip-compile`); check into git

**PyTorch CPU-only deployment:**
- Risk: `requirements.txt` likely specifies `torch>=2.0,cpu` or similar
- Files: Inferred from CLAUDE.md context
- Impact: Training very slow on large datasets; inference latency could exceed acceptable limits for real-time mobile app
- Migration plan: None needed for MVP; plan GPU acceleration for scaling phase if inference latency becomes bottleneck

## Security Considerations

**AWS credentials in environment variables:**
- Risk: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` passed via docker-compose env (line 17-18 in docker-compose.yml)
- Files: `docker-compose.yml`, `api/src/config.py`, `model/src/train.py`
- Current mitigation: LocalStack credentials are test/dummy values; production would use IAM roles
- Recommendations:
  1. Remove hardcoded dummy credentials from docker-compose.yml
  2. Use IAM role attachment (ECS/EKS) in production; boto3 auto-discovers
  3. Add comment in config.py warning against committing real credentials
  4. Rotate test credentials if accidentally exposed

**Base64 image upload not validated for size:**
- Risk: Attacker can POST arbitrarily large base64 strings; no request size limit
- Files: `api/src/main.py` (lines 205-238)
- Impact: Memory exhaustion; DOS
- Recommendations:
  1. Add FastAPI `max_upload_size` middleware
  2. Validate `len(request.image_base64)` before decode
  3. Set reasonable limits (e.g., 10MB max image)

## Missing Critical Features

**No model versioning/registry:**
- Problem: Only one model artifact can be active at a time; no way to support A/B testing, canary rollouts, or quick rollback
- Blocks: Multi-arm bandit optimization, gradual rollout of improved models, comparison testing

**No inference metrics/logging for model monitoring:**
- Problem: Only user-facing prediction logs exist; no per-class accuracy tracking, prediction distribution metrics, or data drift detection
- Blocks: Identifying which waste categories have poor real-world performance; improving dataset balance

**No data validation before training:**
- Problem: Training pipeline assumes all images in S3 are valid; no sanity checks on dataset (missing labels, corrupt files, extreme class imbalance)
- Blocks: Early detection of data quality issues; preventing silent training failure from bad data

---

*Concerns audit: 2026-02-26*
