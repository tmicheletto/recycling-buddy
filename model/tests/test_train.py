"""Unit tests for the training pipeline.

Tests must FAIL before implementation is complete (TDD — constitution Principle II).
Uses tiny synthetic datasets — no S3 access required.
"""

from pathlib import Path
from typing import cast

import torch
import torch.nn as nn
from PIL import Image

from recbuddy.train import build_model, freeze_backbone, get_optimizer, train_one_epoch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tiny_dataset(root: Path, n_classes: int = 3, n_per_class: int = 2) -> Path:
    """Create n_per_class tiny images per class under root/<label>/<n>.jpg."""
    for i in range(n_classes):
        label_dir = root / f"class_{i:02d}"
        label_dir.mkdir(parents=True)
        for j in range(n_per_class):
            img = Image.new("RGB", (64, 64), color=(i * 80, j * 40, 100))
            img.save(label_dir / f"{j}.jpg")
    return root


# ---------------------------------------------------------------------------
# build_model
# ---------------------------------------------------------------------------


def test_build_model_returns_nn_module() -> None:
    model = build_model(num_classes=48)
    assert isinstance(model, nn.Module)


def test_build_model_classifier_head_shape() -> None:
    model = build_model(num_classes=48)
    # EfficientNet-B0 classifier is Sequential; index 1 is the Linear layer
    head = cast(nn.Sequential, model.classifier)[1]
    assert isinstance(head, nn.Linear)
    assert head.out_features == 48


def test_build_model_custom_num_classes() -> None:
    model = build_model(num_classes=10)
    head = cast(nn.Sequential, model.classifier)[1]
    assert isinstance(head, nn.Linear) and head.out_features == 10


# ---------------------------------------------------------------------------
# freeze_backbone
# ---------------------------------------------------------------------------


def test_freeze_backbone_freezes_all_but_classifier() -> None:
    model = build_model(num_classes=48)
    freeze_backbone(model)
    for name, param in model.named_parameters():
        if "classifier" not in name:
            assert not param.requires_grad, f"{name} should be frozen"


def test_freeze_backbone_keeps_classifier_trainable() -> None:
    model = build_model(num_classes=48)
    freeze_backbone(model)
    for name, param in model.named_parameters():
        if "classifier" in name:
            assert param.requires_grad, f"{name} should be trainable"


# ---------------------------------------------------------------------------
# get_optimizer — differential learning rates
# ---------------------------------------------------------------------------


def test_get_optimizer_returns_adamw() -> None:
    model = build_model(num_classes=48)
    optimizer = get_optimizer(model, head_lr=1e-3, backbone_lr=1e-5)
    assert isinstance(optimizer, torch.optim.AdamW)


def test_get_optimizer_backbone_lr_less_than_head_lr() -> None:
    model = build_model(num_classes=48)
    optimizer = get_optimizer(model, head_lr=1e-3, backbone_lr=1e-5)
    lrs = [pg["lr"] for pg in optimizer.param_groups]
    assert min(lrs) < max(lrs), "backbone LR must be less than head LR"


# ---------------------------------------------------------------------------
# train_one_epoch
# ---------------------------------------------------------------------------


def test_train_one_epoch_returns_float_loss(tmp_path: Path) -> None:
    data_dir = _make_tiny_dataset(tmp_path, n_classes=3, n_per_class=2)
    model = build_model(num_classes=3)
    optimizer = get_optimizer(model, head_lr=1e-3, backbone_lr=1e-5)
    criterion = nn.CrossEntropyLoss()

    from torch.utils.data import DataLoader
    from torchvision.datasets import ImageFolder

    from recbuddy.transforms import training_transform

    dataset = ImageFolder(root=str(data_dir), transform=training_transform())
    loader = DataLoader(dataset, batch_size=2, shuffle=True)

    loss = train_one_epoch(model, loader, optimizer, criterion)
    assert isinstance(loss, float)
    assert loss > 0.0
