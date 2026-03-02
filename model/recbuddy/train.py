"""Training pipeline for the waste item classifier.

Two-phase transfer learning on EfficientNet-B0:
  Phase 1 — Backbone frozen, head-only AdamW, CrossEntropyLoss(label_smoothing=0.1)
  Phase 2 — Full fine-tune with differential LRs, SequentialLR warmup→cosine, Mixup

Usage:
    uv run python -m src.train \\
        --s3-bucket recycling-buddy-training \\
        --output-dir model/artifacts/ \\
        --epochs 30 \\
        --seed 42
"""

import argparse
import json
import logging
import random
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torchvision.models as models
from safetensors.torch import save_file
from torch.utils.data import DataLoader
from torchvision.models import EfficientNet_B0_Weights

from recbuddy.dataset import WasteDataset
from recbuddy.labels import ALL_LABELS_LIST

logger = logging.getLogger(__name__)

_EFFICIENTNET_FEATURE_DIM: int = 1280


# ---------------------------------------------------------------------------
# Model construction
# ---------------------------------------------------------------------------


def build_model(num_classes: int = len(ALL_LABELS_LIST)) -> nn.Module:
    """Load EfficientNet-B0 with ImageNet weights and replace the head.

    Args:
        num_classes: Number of output classes.

    Returns:
        EfficientNet-B0 with the final linear layer replaced to output
        ``num_classes`` logits. Weights are pre-loaded from ImageNet.
    """
    model = models.efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
    model.classifier[1] = nn.Linear(_EFFICIENTNET_FEATURE_DIM, num_classes)
    return model


# ---------------------------------------------------------------------------
# Backbone freezing
# ---------------------------------------------------------------------------


def freeze_backbone(model: nn.Module) -> None:
    """Freeze all parameters except the classifier head.

    After this call, only ``model.classifier`` parameters have
    ``requires_grad == True``.  All other parameters are frozen.

    Args:
        model: EfficientNet-B0 returned by :func:`build_model`.
    """
    for name, param in model.named_parameters():
        if "classifier" not in name:
            param.requires_grad = False
        else:
            param.requires_grad = True


def unfreeze_all(model: nn.Module) -> None:
    """Unfreeze every parameter in the model (Phase 2 preparation)."""
    for param in model.parameters():
        param.requires_grad = True


# ---------------------------------------------------------------------------
# Optimizer construction
# ---------------------------------------------------------------------------


def get_optimizer(
    model: nn.Module,
    head_lr: float = 1e-3,
    backbone_lr: float = 1e-5,
) -> torch.optim.AdamW:
    """Return AdamW with separate parameter groups for backbone and head.

    Differential learning rates allow the pre-trained backbone to update
    more slowly than the freshly initialised classifier head.

    Args:
        model: EfficientNet-B0 (may be frozen or unfrozen).
        head_lr: Learning rate for the classifier head.
        backbone_lr: Learning rate for all backbone parameters.

    Returns:
        AdamW optimiser with two parameter groups.
    """
    backbone_params = [p for n, p in model.named_parameters() if "classifier" not in n]
    head_params = [p for n, p in model.named_parameters() if "classifier" in n]
    return torch.optim.AdamW(
        [
            {"params": backbone_params, "lr": backbone_lr},
            {"params": head_params, "lr": head_lr},
        ]
    )


# ---------------------------------------------------------------------------
# Single-epoch training
# ---------------------------------------------------------------------------


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
) -> float:
    """Run one full pass over ``loader`` and return the mean batch loss.

    Args:
        model: The neural network (should be in training mode on entry).
        loader: DataLoader yielding (images, labels) batches.
        optimizer: Optimiser; its ``zero_grad`` and ``step`` are called.
        criterion: Loss function (e.g. ``nn.CrossEntropyLoss``).

    Returns:
        Mean loss across all batches as a plain Python float.
    """
    model.train()
    total_loss = 0.0
    n_batches = 0

    for images, labels in loader:
        optimizer.zero_grad()
        logits = model(images)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


# ---------------------------------------------------------------------------
# Two-phase training loop
# ---------------------------------------------------------------------------


def _mixup_batch(
    images: torch.Tensor,
    labels: torch.Tensor,
    alpha: float = 0.2,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
    """Apply Mixup augmentation to a batch.

    Returns:
        (mixed_images, labels_a, labels_b, lam) for computing the mixed loss.
    """
    lam = float(np.random.beta(alpha, alpha))
    batch_size = images.size(0)
    idx = torch.randperm(batch_size)
    mixed = lam * images + (1 - lam) * images[idx]
    return mixed, labels, labels[idx], lam


def _save_checkpoint(
    model: nn.Module,
    checkpoint_dir: Path,
    epoch: int,
) -> None:
    """Save a safetensors checkpoint after each epoch."""
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    path = checkpoint_dir / f"checkpoint_epoch_{epoch:03d}.safetensors"
    save_file(model.state_dict(), str(path))
    logger.info("Checkpoint saved: %s", path)


def train(
    s3_bucket: str,
    output_dir: Path,
    epochs: int = 30,
    seed: int = 42,
    resume: Optional[str] = None,
    num_classes: int = len(ALL_LABELS_LIST),
    batch_size: int = 32,
    phase1_epochs: int = 5,
    mixup_alpha: float = 0.2,
    label_smoothing: float = 0.1,
    head_lr: float = 1e-3,
    backbone_lr: float = 1e-5,
    fine_tune_head_lr: float = 1e-4,
    s3_endpoint_url: Optional[str] = None,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    region_name: str = "us-east-1",
) -> Path:
    """Run the full two-phase training pipeline.

    Phase 1: Backbone frozen, head-only AdamW with ``head_lr``.
    Phase 2: All weights unfrozen, backbone at ``backbone_lr``, head at
             ``fine_tune_head_lr``; SequentialLR (3-epoch warmup → cosine);
             Mixup augmentation applied per batch.

    Args:
        s3_bucket: S3 bucket containing labeled images.
        output_dir: Directory to write the final safetensors artifact.
        epochs: Total epochs across both phases.
        seed: Random seed for reproducibility.
        resume: Optional path to a safetensors checkpoint to resume from.
        num_classes: Number of output classes.
        batch_size: DataLoader batch size.
        phase1_epochs: Number of epochs for Phase 1 (head-only).
        mixup_alpha: Beta distribution parameter for Mixup.
        label_smoothing: CrossEntropyLoss label smoothing factor.
        head_lr: Learning rate for the head in Phase 1.
        backbone_lr: Learning rate for the backbone in Phase 2.
        fine_tune_head_lr: Learning rate for the head in Phase 2.
        s3_endpoint_url: Optional S3 endpoint for LocalStack.
        aws_access_key_id: Optional AWS access key.
        aws_secret_access_key: Optional AWS secret key.
        region_name: AWS region.

    Returns:
        Path to the saved model artifact.
    """
    _set_seeds(seed)
    output_dir = Path(output_dir)
    checkpoint_dir = output_dir.parent / "checkpoints"

    # ----- data -----
    dataset = WasteDataset(
        s3_bucket=s3_bucket,
        endpoint_url=s3_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name,
    )
    logger.info("Downloading dataset from s3://%s", s3_bucket)
    dataset.download()

    train_ds, val_ds, _ = dataset.get_splits(seed=seed)
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    # ----- model -----
    model = build_model(num_classes=num_classes)
    if resume:
        from safetensors.torch import load_file

        state = load_file(resume)
        model.load_state_dict(state)
        logger.info("Resumed from checkpoint: %s", resume)

    criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

    # -------------------------------------------------------------------
    # Phase 1: head-only training
    # -------------------------------------------------------------------
    logger.info("Phase 1: training head only (%d epochs)", phase1_epochs)
    freeze_backbone(model)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=head_lr
    )

    best_val_acc = 0.0
    for epoch in range(1, phase1_epochs + 1):
        train_loss = train_one_epoch(model, train_loader, optimizer, criterion)
        val_acc = _evaluate(model, val_loader, num_classes)
        if val_acc > best_val_acc:
            best_val_acc = val_acc
        logger.info(
            "Phase1 epoch %d/%d — loss %.4f  val_acc %.4f",
            epoch,
            phase1_epochs,
            train_loss,
            val_acc,
        )
        _save_checkpoint(model, checkpoint_dir, epoch)

    # -------------------------------------------------------------------
    # Phase 2: full fine-tuning with differential LRs
    # -------------------------------------------------------------------
    phase2_epochs = epochs - phase1_epochs
    logger.info("Phase 2: full fine-tuning (%d epochs)", phase2_epochs)
    unfreeze_all(model)
    optimizer2 = get_optimizer(
        model, head_lr=fine_tune_head_lr, backbone_lr=backbone_lr
    )

    warmup_scheduler = torch.optim.lr_scheduler.LinearLR(
        optimizer2, start_factor=0.1, end_factor=1.0, total_iters=3
    )
    cosine_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer2, T_max=max(phase2_epochs - 3, 1)
    )
    scheduler = torch.optim.lr_scheduler.SequentialLR(
        optimizer2,
        schedulers=[warmup_scheduler, cosine_scheduler],
        milestones=[3],
    )

    for epoch in range(1, phase2_epochs + 1):
        model.train()
        total_loss = 0.0
        n_batches = 0
        for images, labels in train_loader:
            mixed_images, labels_a, labels_b, lam = _mixup_batch(
                images, labels, alpha=mixup_alpha
            )
            optimizer2.zero_grad()
            logits = model(mixed_images)
            loss = lam * criterion(logits, labels_a) + (1 - lam) * criterion(
                logits, labels_b
            )
            loss.backward()
            optimizer2.step()
            total_loss += loss.item()
            n_batches += 1

        train_loss = total_loss / max(n_batches, 1)
        scheduler.step()
        val_acc = _evaluate(model, val_loader, num_classes)
        if val_acc > best_val_acc:
            best_val_acc = val_acc
        global_epoch = phase1_epochs + epoch
        logger.info(
            "Phase2 epoch %d/%d — loss %.4f  val_acc %.4f",
            global_epoch,
            epochs,
            train_loss,
            val_acc,
        )
        _save_checkpoint(model, checkpoint_dir, global_epoch)

    # -------------------------------------------------------------------
    # Save final artifact
    # -------------------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)
    version = _next_version(output_dir)
    artifact_path = output_dir / f"efficientnet_b0_recycling_v{version}.safetensors"
    save_file(model.state_dict(), str(artifact_path))
    logger.info("Artifact saved: %s", artifact_path)

    metadata = {
        "epochs": epochs,
        "val_accuracy": round(best_val_acc, 4),
        "seed": seed,
        "num_classes": num_classes,
        "timestamp": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
    }
    meta_path = output_dir / f"training_run_{metadata['timestamp']}.json"
    meta_path.write_text(json.dumps(metadata, indent=2))
    logger.info("Training metadata: %s", meta_path)

    return artifact_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_seeds(seed: int) -> None:
    """Set all random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _evaluate(model: nn.Module, loader: DataLoader, num_classes: int) -> float:
    """Return top-1 accuracy on ``loader``."""
    model.eval()
    correct = total = 0
    with torch.inference_mode():
        for images, labels in loader:
            logits = model(images)
            preds = logits.argmax(dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    return correct / max(total, 1)


def _next_version(output_dir: Path) -> int:
    """Return the next artifact version number (1-based)."""
    existing = list(output_dir.glob("efficientnet_b0_recycling_v*.safetensors"))
    if not existing:
        return 1
    versions = []
    for p in existing:
        stem = p.stem  # e.g. efficientnet_b0_recycling_v3
        try:
            versions.append(int(stem.rsplit("v", 1)[-1]))
        except ValueError:
            pass
    return max(versions, default=0) + 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the Recycling Buddy waste item classifier."
    )
    parser.add_argument(
        "--s3-bucket", required=True, help="S3 bucket with labeled images"
    )
    parser.add_argument(
        "--output-dir",
        default="model/artifacts",
        help="Directory to write the final artifact (default: model/artifacts)",
    )
    parser.add_argument("--epochs", type=int, default=30, help="Total training epochs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--resume",
        default=None,
        help="Path to a safetensors checkpoint to resume from",
    )
    parser.add_argument(
        "--s3-endpoint-url",
        default=None,
        help="S3 endpoint URL (for LocalStack in dev)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()

    import os

    artifact = train(
        s3_bucket=args.s3_bucket,
        output_dir=Path(args.output_dir),
        epochs=args.epochs,
        seed=args.seed,
        resume=args.resume,
        s3_endpoint_url=args.s3_endpoint_url,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    print(f"Training complete. Artifact: {artifact}")
