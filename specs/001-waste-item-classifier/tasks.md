# Tasks: Waste Item Image Classifier

**Input**: Design documents from `/specs/001-waste-item-classifier/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/inference-api.md ✓, quickstart.md ✓

**Tests**: Included — required by Constitution Principle II (TDD mandatory).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to ([US1], [US2], [US3])
- Exact file paths included in all task descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Fix constitution violations and initialize project structure before any implementation begins.

- [x] T001 Fix `model/Dockerfile`: rewrite to use `uv` with multi-stage build (remove `pip install` — constitution Principle IV violation)
- [x] T002 [P] Create `model/pyproject.toml` with PyTorch CPU-only dependencies via `tool.uv.sources` (torch, torchvision, safetensors, pillow, boto3, pytest, ruff, pyrefly)
- [x] T003 [P] Create `model/tests/__init__.py` (empty — enables pytest discovery)
- [x] T004 [P] Create `api/tests/__init__.py` (empty — enables pytest discovery for new API tests)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure that MUST be complete before any user story can begin.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 Update `api/src/config.py`: add `model_artifact_path: str` field to `Settings` (used by the lifespan loader in US1; default to `model/artifacts/efficientnet_b0_recycling_v1.safetensors`)
- [x] T006 [P] Create `model/src/transforms.py`: define `inference_transform()` and `training_transform()` functions returning `torchvision.transforms.v2.Compose` pipelines (Resize 256 → CenterCrop 224 → ToImage → ToDtype float32 → Normalize ImageNet stats for inference; RandomResizedCrop + RandomHorizontalFlip + TrivialAugmentWide + ToImage + ToDtype + Normalize + RandomErasing for training)
- [x] T007 [P] Create `model/src/dataset.py`: define `WasteDataset` class that downloads images from S3 into `model/data/` organised as `<label>/<filename>`, creates a `torchvision.datasets.ImageFolder`, and exposes `get_splits(val_frac=0.15, test_frac=0.15, seed=42) -> tuple[Dataset, Dataset, Dataset]`

**Checkpoint**: Foundation ready — user story implementation can begin.

---

## Phase 3: User Story 1 — Classify a Waste Item from an Image (Priority: P1) 🎯 MVP

**Goal**: A caller submits raw image bytes to `POST /predict` and receives the top-1 waste category label, confidence score, and top-3 alternatives drawn from the 67 defined labels.

**Independent Test**: `curl -X POST http://localhost:8000/predict -F "file=@/path/to/image.jpg"` returns a valid `PredictionResponse` with `label` ∈ ALL_LABELS and `confidence` ∈ [0.0, 1.0].

### Tests for User Story 1 (write first — must FAIL before implementation)

- [x] T008 [P] [US1] Write unit tests for `ClassificationModel` in `api/tests/test_inference.py`: test `from_artifact()` with a tiny random EfficientNet-B0 checkpoint (fixture), test `predict()` returns `ClassificationResult` with `top_prediction.label` ∈ ALL_LABELS, `confidence` ∈ [0,1], `len(alternatives) == 3`, and test `predict()` raises `ValueError` on corrupt bytes
- [x] T009 [P] [US1] Write integration tests for `POST /predict` in `api/tests/test_predict_endpoint.py`: test 200 response shape matches `PredictionResponse` schema with a real JPEG fixture, test 400 on missing file, test 400 on non-image content-type, test that no image file is written to disk after a request

### Implementation for User Story 1

- [x] T010 [US1] Create `api/src/inference.py`: define `CategoryPrediction(label: str, confidence: float)` and `ClassificationResult(top_prediction: CategoryPrediction, alternatives: list[CategoryPrediction])` as frozen dataclasses with type hints (depends on T008 tests existing)
- [x] T011 [US1] Implement `ClassificationModel.from_artifact(artifact_path: str) -> ClassificationModel` in `api/src/inference.py`: call `torch.set_num_threads(4)` and `torch.set_num_interop_threads(1)`, load EfficientNet-B0 with `safetensors.torch.load_file`, replace classifier head with `nn.Linear(1280, 67)`, call `model.eval()` (depends on T010)
- [x] T012 [US1] Implement `ClassificationModel.predict(image_bytes: bytes) -> ClassificationResult` in `api/src/inference.py`: decode via `io.BytesIO` + `PIL.Image.open().convert("RGB")`, apply `inference_transform()` from `model/src/transforms.py`, run `torch.inference_mode()` forward pass, return top-3 `CategoryPrediction` objects using `ALL_LABELS_LIST` index mapping (depends on T010, T006)
- [x] T013 [US1] Add `lifespan` async context manager to `api/src/main.py`: on startup load `ClassificationModel.from_artifact(settings.model_artifact_path)` and store on `app.state.model`; pass `lifespan=lifespan` to `FastAPI(...)` constructor, replacing the current no-lifespan instantiation (depends on T011, T005)
- [x] T014 [US1] Complete `POST /predict` endpoint in `api/src/main.py`: replace the mock stub with `await run_in_threadpool(request.app.state.model.predict, image_bytes)`, map `ClassificationResult` → `PredictionResponse`, keep existing content-type guard (depends on T012, T013)
- [x] T015 [US1] Add structured prediction log entry in `api/src/main.py` after each successful inference: emit `logger.info(json.dumps({"event": "prediction", "timestamp": ..., "predicted_label": ..., "confidence": ...}))` (FR-013; depends on T014)
- [x] T016 [US1] Add `MODEL_ARTIFACT_PATH` to the `api` service `environment` block in `docker-compose.yml` pointing to `/app/model/artifacts/efficientnet_b0_recycling_v1.safetensors` (depends on T005)

**Checkpoint**: `uv run pytest api/tests/test_inference.py api/tests/test_predict_endpoint.py` passes. `POST /predict` returns a valid classification response. User Story 1 is independently functional.

---

## Phase 4: User Story 2 — Train the Model on a Labeled Dataset (Priority: P2)

**Goal**: An ML engineer runs the training script against the S3 dataset and receives a `.safetensors` model artifact in `model/artifacts/` that can immediately be used for inference.

**Independent Test**: `docker-compose run model uv run python -m model.src.train --s3-bucket recycling-buddy-training --output-dir model/artifacts/ --epochs 2 --seed 42` completes without error and writes a `.safetensors` file to `model/artifacts/`.

### Tests for User Story 2 (write first — must FAIL before implementation)

- [x] T017 [P] [US2] Write unit tests for `WasteDataset` in `model/tests/test_dataset.py`: mock S3 client, verify `get_splits()` returns three `Dataset` objects with non-overlapping indices summing to total image count, verify each split image maps to a valid label index ∈ [0, 66] (depends on T007)
- [x] T018 [P] [US2] Write unit tests for training pipeline in `model/tests/test_train.py`: test `build_model(num_classes=67)` returns an `nn.Module` with final linear layer shape `(67,)`, test that Phase 1 freezes backbone parameters (`requires_grad == False`), test that Phase 2 unfreezes with differential LRs (backbone group LR < head group LR), test that one epoch over a tiny 2-image/class dataset reduces loss

### Implementation for User Story 2

- [x] T019 [US2] Create `model/src/train.py`: implement `build_model(num_classes: int = 67) -> nn.Module` — load `EfficientNet_B0_Weights.IMAGENET1K_V1`, replace `model.classifier[1]` with `nn.Linear(1280, num_classes)`, freeze all backbone params (depends on T018 tests existing)
- [x] T020 [US2] Implement two-phase training loop in `model/src/train.py`: Phase 1 trains head only with `AdamW(lr=1e-3)` and `CrossEntropyLoss(label_smoothing=0.1)`; Phase 2 unfreezes all params with differential LRs (backbone `1e-5`, head `1e-4`) and `SequentialLR` (LinearLR warmup 3 epochs → CosineAnnealingLR); Mixup (alpha=0.2) applied in training loop; uses `training_transform()` from `model/src/transforms.py` (depends on T019, T006)
- [x] T021 [US2] Add checkpoint saving in `model/src/train.py`: after each epoch, save `state_dict` via `safetensors.torch.save_file` to `model/checkpoints/checkpoint_epoch_{n}.safetensors`; on training completion, save final artifact as `model/artifacts/efficientnet_b0_recycling_v{version}.safetensors` and write `training_run_{timestamp}.json` metadata (epoch count, val accuracy, seed) (depends on T020)
- [x] T022 [US2] Add CLI entry point to `model/src/train.py`: `if __name__ == "__main__"` block using `argparse` with `--s3-bucket`, `--output-dir`, `--epochs` (default 30), `--seed` (default 42), `--resume` (optional path to checkpoint); set random seeds (`torch.manual_seed`, `random.seed`, `np.random.seed`) (depends on T021)
- [x] T023 [US2] Repurpose `model` docker-compose service: update `command` from `echo "Model service placeholder"` to `uv run python -c "print('Model container ready — use docker-compose run model to execute training/evaluation')"` and confirm volume mounts include `model/artifacts:/app/model/artifacts` and `model/checkpoints:/app/model/checkpoints`

**Checkpoint**: `uv run pytest model/tests/test_dataset.py model/tests/test_train.py` passes. Training script runs end-to-end on a small dataset subset. User Story 2 is independently functional.

---

## Phase 5: User Story 3 — Evaluate Model Performance (Priority: P3)

**Goal**: An ML engineer runs the evaluation script against a trained artifact and test split, receiving a JSON report with per-category top-1 accuracy, overall top-3 accuracy, and a confusion matrix of the most-confused category pairs.

**Independent Test**: `docker-compose run model uv run python -m model.src.evaluate --artifact model/artifacts/efficientnet_b0_recycling_v1.safetensors --s3-bucket recycling-buddy-training --split test` outputs a valid JSON object with keys `overall_top1_accuracy`, `overall_top3_accuracy`, `per_category`, and `confused_pairs`.

### Tests for User Story 3 (write first — must FAIL before implementation)

- [x] T024 [US3] Write unit tests for evaluation pipeline in `model/tests/test_evaluate.py`: mock a tiny model returning fixed logits, verify `compute_metrics()` returns correct top-1 and top-3 accuracy for known inputs, verify `per_category` dict has an entry for every label in `ALL_LABELS_LIST`, verify `confused_pairs` is sorted descending by confusion count (depends on T017 dataset fixture available)

### Implementation for User Story 3

- [x] T025 [US3] Create `model/src/evaluate.py`: implement `load_artifact(path: str) -> nn.Module` that mirrors the loading logic from `api/src/inference.py` (load safetensors state dict into EfficientNet-B0 with 67-class head, `.eval()`); implement `compute_metrics(model, dataset, labels) -> dict` returning `overall_top1_accuracy`, `overall_top3_accuracy`, `per_category: dict[str, float]`, `confused_pairs: list[tuple[str, str, int]]` (depends on T024 tests existing, T006)
- [x] T026 [US3] Add CLI entry point to `model/src/evaluate.py`: `if __name__ == "__main__"` block with `argparse` supporting `--artifact`, `--s3-bucket`, `--split` (default `test`); print JSON report to stdout; flag categories where `per_category[label] < 0.60` with a warning line to stderr (SC-003 gate) (depends on T025)

**Checkpoint**: `uv run pytest model/tests/test_evaluate.py` passes. Evaluation script produces a complete JSON report. User Story 3 is independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Code quality, constitution compliance, and validation across all stories.

- [x] T027 [P] Run `uv run ruff format . && uv run ruff check . --fix` in both `model/` and `api/` directories; fix all reported issues (constitution: Development Workflow step 2)
- [x] T028 [P] Run `pyrefly check` in both `model/` and `api/` directories; fix all type errors in new files: `api/src/inference.py`, `model/src/transforms.py`, `model/src/dataset.py`, `model/src/train.py`, `model/src/evaluate.py` (constitution: Technology Standards)
- [x] T029 Update `model/README.md`: replace placeholder content with real usage instructions from `quickstart.md` — train command, evaluate command, artifact path configuration
- [x] T030 Validate `docker-compose up --build` starts cleanly with the new `model/Dockerfile`; verify `POST /predict` returns a valid response with a trained artifact present (constitution Principle IV end-to-end gate)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001–T004 can all start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion — T005–T007 block all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — can start after T005, T006 done; T007 not required for US1
- **US2 (Phase 4)**: Depends on Foundational (Phase 2) — requires T006 (transforms) and T007 (dataset)
- **US3 (Phase 5)**: Depends on US2 (Phase 4) — requires a trained artifact to evaluate; also depends on T007
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends on T005 (config), T006 (transforms) — independent of US2 and US3
- **US2 (P2)**: Depends on T006 (transforms), T007 (dataset) — independent of US1 and US3
- **US3 (P3)**: Depends on US2 completion (needs a trained artifact) — independent of US1

### Within Each User Story

- Tests MUST be written first and FAIL before implementation begins (Constitution Principle II)
- Value objects / data classes before services
- Services before endpoint integration
- Logging/observability alongside the endpoint (not deferred)

### Parallel Opportunities

Within Setup (Phase 1): T001, T002, T003, T004 are all parallel

Within Foundational (Phase 2): T005, T006, T007 are all parallel

Within US1 (Phase 3):
- T008 and T009 are parallel (different test files)
- T010 can start alongside tests (different file)

Within US2 (Phase 4):
- T017 and T018 are parallel (different test files)
- T019 can start when T018 exists

Within Polish (Phase 6):
- T027 and T028 are parallel (ruff and pyrefly are independent tools)

---

## Parallel Example: User Story 1

```bash
# Write all US1 tests in parallel first:
Task: "T008 — api/tests/test_inference.py"
Task: "T009 — api/tests/test_predict_endpoint.py"
Task: "T010 — api/src/inference.py value objects" (no test dependency)

# Then implement in sequence:
T011 → T012 → T013 → T014 → T015 → T016
```

## Parallel Example: User Story 2

```bash
# Write all US2 tests in parallel first:
Task: "T017 — model/tests/test_dataset.py"
Task: "T018 — model/tests/test_train.py"

# Then implement in sequence:
T019 → T020 → T021 → T022 → T023
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (fix Dockerfile, add pyproject.toml)
2. Complete Phase 2: Foundational (config, transforms, dataset)
3. Complete Phase 3: User Story 1 (inference + /predict endpoint)
4. **STOP and VALIDATE**: `uv run pytest api/tests/` passes; `POST /predict` works end-to-end with a manually placed model artifact
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → project compiles and tests can run
2. Add US1 → `POST /predict` works → Deploy/Demo (MVP!)
3. Add US2 → training pipeline works → first real model artifact produced
4. Add US3 → evaluation pipeline confirms model quality meets ≥ 85% accuracy gate
5. Polish → all lint/type checks pass; Docker stack starts cleanly

### Parallel Team Strategy

With two developers:
- Developer A: US1 (T008–T016) — API inference integration
- Developer B: US2 (T017–T023) — model training pipeline

Both start after Phase 2 completes. US3 and Polish follow once both are done.

---

## Notes

- [P] tasks operate on different files with no blocking dependency — safe to run concurrently
- [Story] label maps each task to a specific user story for traceability
- TDD is mandatory (constitution Principle II): test tasks marked with "write first — must FAIL"
- Test fixtures for US1 should use a tiny randomly-initialised EfficientNet-B0 model (not a real artifact) to keep tests fast and dependency-free
- Model artifact path is runtime-configurable via `MODEL_ARTIFACT_PATH` env var — no artifact is required at build time
- Commit after each checkpoint using Conventional Commits format (`feat:`, `fix:`, `test:`, `chore:`)
- Working tree MUST be clean before each commit (constitution Development Workflow step 6)
