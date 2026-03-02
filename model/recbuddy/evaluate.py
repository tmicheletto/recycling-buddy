"""Evaluation pipeline for the waste item classifier.

Loads a trained safetensors artifact and computes:
  - overall top-1 and top-3 accuracy
  - per-category top-1 accuracy
  - most-confused category pairs (sorted by confusion count)

Usage:
    uv run python -m src.evaluate \\
        --artifact model/artifacts/efficientnet_b0_recycling_v1.safetensors \\
        --s3-bucket recycling-buddy-training \\
        --split test
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict

import torch
import torch.nn as nn
import torchvision.models as models
from safetensors.torch import load_file
from torch.utils.data import DataLoader

from recbuddy.labels import ALL_LABELS_LIST

logger = logging.getLogger(__name__)

_EFFICIENTNET_FEATURE_DIM: int = 1280
_NUM_CLASSES: int = len(ALL_LABELS_LIST)

# Low-accuracy threshold — categories below this trigger a stderr warning.
_LOW_ACCURACY_THRESHOLD: float = 0.60


# ---------------------------------------------------------------------------
# Artifact loading
# ---------------------------------------------------------------------------


def load_artifact(artifact_path: str, num_classes: int = _NUM_CLASSES) -> nn.Module:
    """Load a trained EfficientNet-B0 from a safetensors file.

    Args:
        artifact_path: Path to a ``.safetensors`` state-dict file.
        num_classes: Number of output classes the model was trained with.

    Returns:
        EfficientNet-B0 in ``eval()`` mode with loaded weights.

    Raises:
        FileNotFoundError: If ``artifact_path`` does not exist.
    """
    if not os.path.exists(artifact_path):
        raise FileNotFoundError(
            f"Model artifact not found: {artifact_path}. "
            "Run the training pipeline to produce an artifact first."
        )

    net = models.efficientnet_b0(weights=None)
    net.classifier[1] = nn.Linear(_EFFICIENTNET_FEATURE_DIM, num_classes)
    net.load_state_dict(load_file(artifact_path))
    net.eval()
    logger.info("Loaded artifact: %s", artifact_path)
    return net


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------


def compute_metrics(
    model: nn.Module,
    loader: DataLoader,
    labels: list[str],
) -> dict:
    """Compute classification metrics over a DataLoader.

    Args:
        model: Trained EfficientNet-B0 in eval mode.
        loader: DataLoader yielding (images, label_indices) batches.
        labels: List of label strings, where ``labels[i]`` is the class name
                for class index ``i``.

    Returns:
        Dictionary with keys:
          - ``overall_top1_accuracy``: float in [0, 1]
          - ``overall_top3_accuracy``: float in [0, 1]
          - ``per_category``: dict[str, float] — top-1 per label
          - ``confused_pairs``: list of (true_label, pred_label, count)
                sorted descending by count; only misclassifications.
    """
    num_classes = len(labels)
    # per_class_correct[i] = (correct_top1, total)
    per_class_correct: list[int] = [0] * num_classes
    per_class_total: list[int] = [0] * num_classes
    # confusion_counts[(true_idx, pred_idx)] = count (only misclassifications)
    confusion_counts: dict[tuple[int, int], int] = defaultdict(int)

    top1_correct = 0
    top3_correct = 0
    total = 0

    model.eval()
    with torch.inference_mode():
        for images, label_indices in loader:
            logits = model(images)  # (B, num_classes)
            batch_size = label_indices.size(0)

            # Top-1
            top1_preds = logits.argmax(dim=1)

            # Top-3 (clamp to available classes)
            k = min(3, num_classes)
            top3_preds = logits.topk(k, dim=1).indices  # (B, k)

            for b in range(batch_size):
                true_idx = int(label_indices[b])
                pred_idx = int(top1_preds[b])

                # top-1
                if pred_idx == true_idx:
                    top1_correct += 1
                    per_class_correct[true_idx] += 1
                else:
                    confusion_counts[(true_idx, pred_idx)] += 1

                # top-3
                if true_idx in top3_preds[b].tolist():
                    top3_correct += 1

                per_class_total[true_idx] += 1

            total += batch_size

    overall_top1 = top1_correct / max(total, 1)
    overall_top3 = top3_correct / max(total, 1)

    per_category = {
        labels[i]: per_class_correct[i] / max(per_class_total[i], 1)
        for i in range(num_classes)
    }

    # Build sorted confused pairs list
    confused_pairs: list[tuple[str, str, int]] = [
        (labels[true_idx], labels[pred_idx], count)
        for (true_idx, pred_idx), count in confusion_counts.items()
    ]
    confused_pairs.sort(key=lambda x: x[2], reverse=True)

    return {
        "overall_top1_accuracy": overall_top1,
        "overall_top3_accuracy": overall_top3,
        "per_category": per_category,
        "confused_pairs": confused_pairs,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a trained Recycling Buddy waste item classifier."
    )
    parser.add_argument(
        "--artifact",
        required=True,
        help="Path to the .safetensors model artifact",
    )
    parser.add_argument(
        "--s3-bucket",
        required=True,
        help="S3 bucket containing labeled images",
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=["train", "val", "test"],
        help="Which dataset split to evaluate (default: test)",
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

    from torch.utils.data import DataLoader

    from recbuddy.dataset import WasteDataset

    # Resolve the label list from the dataset
    dataset_obj = WasteDataset(
        s3_bucket=args.s3_bucket,
        endpoint_url=args.s3_endpoint_url,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    dataset_obj.download()
    train_ds, val_ds, test_ds = dataset_obj.get_splits()

    split_map = {"train": train_ds, "val": val_ds, "test": test_ds}
    eval_ds = split_map[args.split]
    loader = DataLoader(eval_ds, batch_size=32, shuffle=False, num_workers=0)

    # Derive label list from class_to_idx (sorted by index)
    class_to_idx = dataset_obj.class_to_idx
    label_list = sorted(class_to_idx.keys(), key=lambda k: class_to_idx[k])

    model = load_artifact(args.artifact, num_classes=len(label_list))
    metrics = compute_metrics(model, loader, label_list)

    # Print JSON report to stdout
    print(json.dumps(metrics, indent=2))

    # Warn on categories below accuracy threshold
    low_accuracy = [
        (lbl, acc)
        for lbl, acc in metrics["per_category"].items()
        if acc < _LOW_ACCURACY_THRESHOLD
    ]
    if low_accuracy:
        for lbl, acc in sorted(low_accuracy, key=lambda x: x[1]):
            print(
                f"WARNING: {lbl} accuracy {acc:.2%} is below "
                f"{_LOW_ACCURACY_THRESHOLD:.0%} threshold",
                file=sys.stderr,
            )
