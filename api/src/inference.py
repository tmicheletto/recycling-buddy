"""In-process image classifier for waste item categorisation.

This module is the single integration point between FastAPI and the PyTorch
model. It owns:
  - Value objects returned to callers (CategoryPrediction, ClassificationResult)
  - ClassificationModel: loads a safetensors artifact, runs thread-safe inference

Design constraints (from spec / constitution):
  - Loaded once at app startup via FastAPI lifespan; shared across requests
  - Thread-safe: model.eval() + torch.inference_mode(); no shared mutable state
  - Images are NEVER stored; bytes are discarded after each predict() call
  - Inference is run via run_in_threadpool() from async routes (non-blocking)
"""

import io
import logging
from dataclasses import dataclass

import torch
import torch.nn as nn
import torchvision.models as models
from PIL import Image, UnidentifiedImageError
from safetensors.torch import load_file
from torchvision.transforms import v2 as T

from src.labels import ALL_LABELS_LIST

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NUM_CLASSES: int = len(ALL_LABELS_LIST)  # 67
_EFFICIENTNET_FEATURE_DIM: int = 1280

# ImageNet normalisation — matches EfficientNet_B0_Weights.IMAGENET1K_V1
_IMAGENET_MEAN: list[float] = [0.485, 0.456, 0.406]
_IMAGENET_STD: list[float] = [0.229, 0.224, 0.225]

# Set PyTorch thread counts once at module load time.
# set_num_interop_threads cannot be changed after the first parallel operation.
torch.set_num_interop_threads(1)

# Composed once at import time; stateless and thread-safe
_INFERENCE_TRANSFORM: T.Compose = T.Compose(
    [
        T.Resize(256),
        T.CenterCrop(224),
        T.ToImage(),
        T.ToDtype(torch.float32, scale=True),
        T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
    ]
)

# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CategoryPrediction:
    """A single label-confidence pair from the classifier."""

    label: str
    confidence: float


@dataclass(frozen=True)
class ClassificationResult:
    """Output of a single inference call.

    alternatives always has exactly 3 entries, ordered confidence descending.
    alternatives[0] is identical to top_prediction.
    """

    top_prediction: CategoryPrediction
    alternatives: list[CategoryPrediction]


# ---------------------------------------------------------------------------
# ClassificationModel
# ---------------------------------------------------------------------------


class ClassificationModel:
    """Wraps a PyTorch EfficientNet-B0 model for thread-safe CPU inference.

    Load once at application startup (FastAPI lifespan). Safe for concurrent
    access: model.eval() is set permanently; each predict() call creates its
    own tensors via torch.inference_mode().
    """

    def __init__(self, net: nn.Module) -> None:
        self._net = net

    @classmethod
    def from_artifact(cls, artifact_path: str) -> "ClassificationModel":
        """Load a trained model from a safetensors file.

        Sets torch thread counts before any tensor operations to prevent
        CPU over-subscription when serving up to 10 concurrent requests.

        Args:
            artifact_path: Path to a .safetensors state-dict file.

        Returns:
            ClassificationModel ready for concurrent inference.

        Raises:
            FileNotFoundError: If artifact_path does not exist.
        """
        import os

        if not os.path.exists(artifact_path):
            raise FileNotFoundError(
                f"Model artifact not found: {artifact_path}. "
                "Run the training pipeline to produce an artifact first."
            )

        # set_num_threads can be called per-load; set_num_interop_threads
        # is handled once at module level above.
        torch.set_num_threads(4)

        net = models.efficientnet_b0(weights=None)
        net.classifier[1] = nn.Linear(_EFFICIENTNET_FEATURE_DIM, _NUM_CLASSES)
        net.load_state_dict(load_file(artifact_path))
        net.eval()  # Disable dropout / BatchNorm training mode; never toggled back

        logger.info("Loaded model artifact: %s", artifact_path)
        return cls(net)

    def predict(self, image_bytes: bytes) -> ClassificationResult:
        """Classify raw image bytes.

        Thread-safe: no shared mutable state. Call via run_in_threadpool()
        from async FastAPI routes so the event loop is not blocked.

        Args:
            image_bytes: Raw bytes in JPEG, PNG, or WEBP format.
                         NOT stored or written to disk.

        Returns:
            ClassificationResult with top prediction and top-3 alternatives.

        Raises:
            ValueError: If image_bytes cannot be decoded as a valid image.
        """
        tensor = self._decode(image_bytes)

        with torch.inference_mode():
            logits = self._net(tensor)  # (1, 67)
            probs = torch.softmax(logits, dim=1).squeeze(0)  # (67,)

        top3_indices = probs.argsort(descending=True)[:3].tolist()

        alternatives = [
            CategoryPrediction(
                label=ALL_LABELS_LIST[i],
                confidence=float(probs[i]),
            )
            for i in top3_indices
        ]

        return ClassificationResult(
            top_prediction=alternatives[0],
            alternatives=alternatives,
        )

    @staticmethod
    def _decode(image_bytes: bytes) -> torch.Tensor:
        """Decode bytes → PIL RGB → normalised (1, 3, 224, 224) tensor.

        The PIL Image is not persisted; memory is released after transform.
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img = img.convert("RGB")
                tensor = _INFERENCE_TRANSFORM(img)
        except (UnidentifiedImageError, Exception) as exc:
            raise ValueError(
                f"Cannot decode image bytes: {exc}. Supported formats: JPEG, PNG, WEBP."
            ) from exc

        return tensor.unsqueeze(0)  # add batch dimension: (1, 3, 224, 224)
