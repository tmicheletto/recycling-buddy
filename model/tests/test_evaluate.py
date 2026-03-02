"""Unit tests for the evaluation pipeline.

Tests must FAIL before implementation is complete (TDD — constitution Principle II).
Uses tiny synthetic models and datasets — no S3 access required.
"""

from pathlib import Path

import pytest
import torch.nn as nn
from PIL import Image
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

from recbuddy.evaluate import compute_metrics, load_artifact

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Use 3 labels matching how ImageFolder sorts them alphabetically
LABELS = ["class_00", "class_01", "class_02"]
NUM_CLASSES = len(LABELS)


def _make_tiny_dataset(root: Path, n_classes: int = 3, n_per_class: int = 4) -> Path:
    """Create a tiny ImageFolder-compatible dataset under root."""
    for i in range(n_classes):
        label_dir = root / f"class_{i:02d}"
        label_dir.mkdir(parents=True)
        for j in range(n_per_class):
            img = Image.new("RGB", (64, 64), color=(i * 80, j * 20, 100))
            img.save(label_dir / f"{j}.jpg")
    return root


def _tiny_efficientnet(num_classes: int = 3) -> nn.Module:
    """Return a tiny randomly-initialised EfficientNet-B0."""
    import torchvision.models as models

    net = models.efficientnet_b0(weights=None)
    net.classifier[1] = nn.Linear(1280, num_classes)
    net.eval()
    return net


def _save_tiny_artifact(tmp_path: Path, num_classes: int = 3) -> Path:
    """Save a tiny EfficientNet-B0 as a safetensors file and return the path."""
    from safetensors.torch import save_file

    net = _tiny_efficientnet(num_classes)
    artifact_path = tmp_path / "tiny_model.safetensors"
    save_file(net.state_dict(), str(artifact_path))
    return artifact_path


# ---------------------------------------------------------------------------
# load_artifact
# ---------------------------------------------------------------------------


def test_load_artifact_returns_nn_module(tmp_path: Path) -> None:
    artifact_path = _save_tiny_artifact(tmp_path, num_classes=NUM_CLASSES)
    model = load_artifact(str(artifact_path), num_classes=NUM_CLASSES)
    assert isinstance(model, nn.Module)


def test_load_artifact_model_is_in_eval_mode(tmp_path: Path) -> None:
    artifact_path = _save_tiny_artifact(tmp_path, num_classes=NUM_CLASSES)
    model = load_artifact(str(artifact_path), num_classes=NUM_CLASSES)
    assert not model.training


def test_load_artifact_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_artifact(
            str(tmp_path / "nonexistent.safetensors"), num_classes=NUM_CLASSES
        )


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------


@pytest.fixture
def dataset_and_loader(tmp_path: Path):
    data_dir = _make_tiny_dataset(tmp_path, n_classes=NUM_CLASSES, n_per_class=4)
    from recbuddy.transforms import inference_transform

    ds = ImageFolder(root=str(data_dir), transform=inference_transform())
    loader = DataLoader(ds, batch_size=4, shuffle=False)
    return ds, loader


def test_compute_metrics_returns_required_keys(dataset_and_loader) -> None:
    ds, loader = dataset_and_loader
    model = _tiny_efficientnet(num_classes=NUM_CLASSES)
    result = compute_metrics(model, loader, LABELS)
    assert "overall_top1_accuracy" in result
    assert "overall_top3_accuracy" in result
    assert "per_category" in result
    assert "confused_pairs" in result


def test_compute_metrics_overall_top1_in_range(dataset_and_loader) -> None:
    ds, loader = dataset_and_loader
    model = _tiny_efficientnet(num_classes=NUM_CLASSES)
    result = compute_metrics(model, loader, LABELS)
    assert 0.0 <= result["overall_top1_accuracy"] <= 1.0


def test_compute_metrics_overall_top3_in_range(dataset_and_loader) -> None:
    ds, loader = dataset_and_loader
    model = _tiny_efficientnet(num_classes=NUM_CLASSES)
    result = compute_metrics(model, loader, LABELS)
    assert 0.0 <= result["overall_top3_accuracy"] <= 1.0


def test_compute_metrics_per_category_has_all_labels(dataset_and_loader) -> None:
    ds, loader = dataset_and_loader
    model = _tiny_efficientnet(num_classes=NUM_CLASSES)
    result = compute_metrics(model, loader, LABELS)
    for label in LABELS:
        assert label in result["per_category"]


def test_compute_metrics_per_category_values_in_range(dataset_and_loader) -> None:
    ds, loader = dataset_and_loader
    model = _tiny_efficientnet(num_classes=NUM_CLASSES)
    result = compute_metrics(model, loader, LABELS)
    for label, acc in result["per_category"].items():
        assert 0.0 <= acc <= 1.0, f"{label} accuracy {acc} out of range"


def test_compute_metrics_confused_pairs_sorted_descending(dataset_and_loader) -> None:
    ds, loader = dataset_and_loader
    model = _tiny_efficientnet(num_classes=NUM_CLASSES)
    result = compute_metrics(model, loader, LABELS)
    pairs = result["confused_pairs"]
    # Each pair is (true_label, pred_label, count) — sorted by count descending
    counts = [p[2] for p in pairs]
    assert counts == sorted(counts, reverse=True)


def test_compute_metrics_top3_ge_top1(dataset_and_loader) -> None:
    """Top-3 accuracy must be >= top-1 accuracy."""
    ds, loader = dataset_and_loader
    model = _tiny_efficientnet(num_classes=NUM_CLASSES)
    result = compute_metrics(model, loader, LABELS)
    assert result["overall_top3_accuracy"] >= result["overall_top1_accuracy"]
