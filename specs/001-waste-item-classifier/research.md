# Research: Waste Item Image Classifier

**Phase**: 0 — Pre-design research
**Feature**: `001-waste-item-classifier`
**Date**: 2026-02-25

---

## R-01: ML Framework Selection

**Decision**: PyTorch + torchvision

**Rationale**:
- Fastest CPU single-image inference in 2025 benchmarks (up to 3x faster than Keras for small batch sizes due to Keras dispatch overhead)
- Official `uv` + PyTorch CPU integration guide exists (`tool.uv.sources` in `pyproject.toml`)
- Most industrially-relevant portfolio signal in 2025 (~55% production share, ~80% of NeurIPS papers)
- `torchvision.models` provides first-class pretrained EfficientNet/MobileNet backbones
- Explicit Python training loops are more legible for a portfolio than Keras's high-level abstractions

**Alternatives considered**:
- **TensorFlow/Keras**: Ruled out — measurably slower CPU latency, heavier uv dependency tree, development in flux (tf.lite deprecated, Keras 3 now multi-backend)
- **scikit-learn**: Ruled out — cannot produce a CNN classifier; could only serve as linear probe on top of frozen torchvision features (adds complexity, forfeits fine-tuning accuracy)

---

## R-02: Pretrained Backbone Selection

**Decision**: EfficientNet-B0 (`torchvision.models.efficientnet_b0`)

**Rationale**:
- ~20.5 MB disk (well under 100 MB constraint, with headroom)
- 77.7% ImageNet top-1 — highest accuracy of small-footprint candidates
- CPU inference for a 224×224 image: ~100–250 ms (well under 500 ms budget)
- Compound scaling architecture gives better feature expressiveness per FLOP than MobileNet when source/target domains differ moderately (which applies here: ImageNet → recycling waste)
- Available directly: `EfficientNet_B0_Weights.IMAGENET1K_V1`

**Alternatives considered**:
- **MobileNetV3-Large** (~21 MB, 75.2% ImageNet top-1): ~2–3% lower accuracy ceiling; valid fallback if 500 ms budget is approached on slow hardware
- **MobileNetV3-Small** (~9 MB, 67.4% top-1): Too low an accuracy ceiling for 67-class fine-grained classification with limited data
- **ResNet-50** (~98 MB, 25M params): Exceeds 100 MB model size limit; too slow on CPU without quantization

---

## R-03: Training Strategy for Small Datasets (50–500 images/class)

**Decision**: Two-phase transfer learning — freeze backbone then unfreeze

**Rationale**:
With as few as 50 images per class, training the full network from scratch causes catastrophic forgetting before new-domain features stabilize. The freeze→unfreeze approach is the validated standard practice for small-dataset transfer learning.

**Phase 1** (~10 epochs):
- Freeze all backbone parameters; train only the new 67-class head
- Replace EfficientNet-B0's 1000-class head with `nn.Linear(1280, 67)` (feature dim: 1280)
- Head LR: 1e-3; keep backbone BatchNorm in eval mode to preserve pretrained statistics

**Phase 2** (~20 epochs):
- Unfreeze all parameters using differential learning rates
- Backbone LR: 1e-5 (low, to preserve pretrained representations)
- Head LR: 1e-4

**Optimizer**: AdamW with weight decay 5e-3 (decoupled weight decay matters for small-dataset generalization)

**LR Schedule**: Linear warmup (3 epochs) → cosine annealing to 1e-7

**Loss**: `CrossEntropyLoss(label_smoothing=0.1)` to prevent overconfident predictions

---

## R-04: Data Augmentation Strategy

**Decision**: TrivialAugmentWide + Mixup

**Training transforms**:
1. `RandomResizedCrop(224, scale=(0.7, 1.0))`
2. `RandomHorizontalFlip()`
3. `TrivialAugmentWide()` — preferred over RandAugment for small datasets (no hyperparameters to tune)
4. `ToTensor()` → `Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])` (ImageNet statistics)
5. `RandomErasing(p=0.25)` — patch dropout for robustness
6. Mixup (alpha=0.2) applied in training loop — improves calibration and decision boundary smoothness

**Inference/validation transforms**: `Resize(256)` → `CenterCrop(224)` → `ToTensor()` → `Normalize()`

**Rationale**: Aggressive augmentation is critical at 50–500 images/class to prevent overfitting. TrivialAugmentWide has no hyperparameters to tune, making it safe for small datasets.

---

## R-05: Model Serialization Format

**Decision**: `safetensors` (Hugging Face)

**Rationale**:
- Loads ~100x faster than pickle-based `.pth` on CPU
- Externally audited as secure (no arbitrary code execution risk unlike pickle)
- Emerging standard in the PyTorch ecosystem
- ~20.5 MB file for EfficientNet-B0 state dict — well under 100 MB

**Alternatives considered**:
- **`torch.save(state_dict())`** (`.pth`): Uses Python pickle — allows arbitrary code execution on load; security risk for shared artifacts
- **TorchScript**: Adds compilation complexity; no performance benefit for CPU-only Python inference; breaks with model code changes
- **ONNX**: Over-engineered for an in-process call; requires separate runtime

**Loading pattern**:
```python
from safetensors.torch import load_file
import torchvision.models as models
import torch

model = models.efficientnet_b0(weights=None)
model.classifier[1] = torch.nn.Linear(1280, 67)
model.load_state_dict(load_file("artifact.safetensors"))
model.eval()
```

---

## R-06: FastAPI In-Process Integration Pattern

**Decision**: Model loaded once at app lifespan startup; inference called via `run_in_threadpool()`

**Rationale**:
- PyTorch CPU inference with `model.eval()` is thread-safe — concurrent forward passes on the same model instance are supported
- `async def predict()` + `await run_in_threadpool(classify, image_bytes)` keeps the asyncio event loop unblocked during CPU-bound inference
- Plain `def predict()` would work too (FastAPI runs sync routes in a thread pool), but `async def` with explicit `run_in_threadpool` gives clearer intent
- Model loaded in FastAPI lifespan event (not module-level) gives proper startup/shutdown lifecycle management

**Threading note**: Set `torch.set_num_threads(4)` at startup to control PyTorch's internal thread pool and avoid CPU over-subscription when serving up to 10 concurrent requests.

**Integration path**: `./model:/app/model` is already mounted in the API Docker container at `/app/model`. Since the API's WORKDIR is `/app`, `from model.src.classifier import classify` resolves without additional PYTHONPATH configuration.

**Alternatives considered**:
- **Module-level singleton**: Works but is harder to test and control startup order
- **FastAPI dependency injection**: More testable but adds indirection for a single model instance (YAGNI)
- **Separate HTTP service**: Ruled out by clarification Q1 — in-process only

---

## R-07: Constitution Compliance Check

**Pre-plan violations identified**:

| Item | Status | Resolution |
|------|--------|------------|
| `model/Dockerfile` uses `pip install` | VIOLATION (Principle IV + Technology Standards) | Replace with `uv` + multi-stage build |
| `model/` has no `pyproject.toml` | VIOLATION (Technology Standards) | Add `pyproject.toml` with uv configuration |
| `model` docker-compose service is placeholder `echo` | ACCEPTABLE | Repurpose as training/evaluation runner; inference is in-process with API |

**Spec vs Constitution discrepancy**:

| Metric | Spec | Constitution | Binding |
|--------|------|--------------|---------|
| Accuracy target | >80% top-1 | >85% validation | **Constitution** (stricter) |
| Inference latency | <2 seconds | <500ms | **Constitution** (stricter) |
| Model size | not stated | <100MB | **Constitution** |

The constitution's targets are used as binding constraints throughout this plan. The spec's weaker targets do not supersede the constitution.
