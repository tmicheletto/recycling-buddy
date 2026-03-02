"""Unit tests for ClassificationModel.

Tests must FAIL before implementation exists (TDD — constitution Principle II).
Uses a tiny random EfficientNet-B0 artifact so tests are fast and
independent of any real trained model.
"""

import io

import pytest
import torch
import torchvision.models as models
from PIL import Image
from safetensors.torch import save_file

from app.inference import CategoryPrediction, ClassificationModel, ClassificationResult
from recbuddy.labels import ALL_LABELS_LIST


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_jpeg_bytes() -> bytes:
    """Minimal valid 32×32 red JPEG."""
    img = Image.new("RGB", (32, 32), color=(200, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def model_artifact_path(tmp_path) -> str:
    """Create a tiny random EfficientNet-B0 safetensors artifact."""
    net = models.efficientnet_b0(weights=None)
    net.classifier[1] = torch.nn.Linear(1280, len(ALL_LABELS_LIST))
    path = tmp_path / "test_model.safetensors"
    save_file(net.state_dict(), str(path))
    return str(path)


# ---------------------------------------------------------------------------
# ClassificationModel.from_artifact
# ---------------------------------------------------------------------------


def test_from_artifact_returns_instance(model_artifact_path: str) -> None:
    model = ClassificationModel.from_artifact(model_artifact_path)
    assert isinstance(model, ClassificationModel)


def test_from_artifact_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        ClassificationModel.from_artifact("/nonexistent/path/model.safetensors")


# ---------------------------------------------------------------------------
# ClassificationModel.predict
# ---------------------------------------------------------------------------


def test_predict_returns_classification_result(
    model_artifact_path: str, valid_jpeg_bytes: bytes
) -> None:
    model = ClassificationModel.from_artifact(model_artifact_path)
    result = model.predict(valid_jpeg_bytes)
    assert isinstance(result, ClassificationResult)


def test_predict_top_prediction_label_in_all_labels(
    model_artifact_path: str, valid_jpeg_bytes: bytes
) -> None:
    model = ClassificationModel.from_artifact(model_artifact_path)
    result = model.predict(valid_jpeg_bytes)
    assert result.top_prediction.label in ALL_LABELS_LIST


def test_predict_confidence_in_unit_interval(
    model_artifact_path: str, valid_jpeg_bytes: bytes
) -> None:
    model = ClassificationModel.from_artifact(model_artifact_path)
    result = model.predict(valid_jpeg_bytes)
    assert 0.0 <= result.top_prediction.confidence <= 1.0


def test_predict_alternatives_has_three_entries(
    model_artifact_path: str, valid_jpeg_bytes: bytes
) -> None:
    model = ClassificationModel.from_artifact(model_artifact_path)
    result = model.predict(valid_jpeg_bytes)
    assert len(result.alternatives) == 3


def test_predict_alternatives_index_zero_matches_top(
    model_artifact_path: str, valid_jpeg_bytes: bytes
) -> None:
    model = ClassificationModel.from_artifact(model_artifact_path)
    result = model.predict(valid_jpeg_bytes)
    assert result.alternatives[0].label == result.top_prediction.label
    assert result.alternatives[0].confidence == result.top_prediction.confidence


def test_predict_all_alternatives_labels_in_all_labels(
    model_artifact_path: str, valid_jpeg_bytes: bytes
) -> None:
    model = ClassificationModel.from_artifact(model_artifact_path)
    result = model.predict(valid_jpeg_bytes)
    for pred in result.alternatives:
        assert pred.label in ALL_LABELS_LIST


def test_predict_alternatives_sorted_descending(
    model_artifact_path: str, valid_jpeg_bytes: bytes
) -> None:
    model = ClassificationModel.from_artifact(model_artifact_path)
    result = model.predict(valid_jpeg_bytes)
    confidences = [p.confidence for p in result.alternatives]
    assert confidences == sorted(confidences, reverse=True)


def test_predict_raises_value_error_on_corrupt_bytes(
    model_artifact_path: str,
) -> None:
    model = ClassificationModel.from_artifact(model_artifact_path)
    with pytest.raises(ValueError):
        model.predict(b"this-is-not-an-image")


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


def test_category_prediction_is_frozen() -> None:
    pred = CategoryPrediction(label="cardboard", confidence=0.9)
    with pytest.raises((AttributeError, TypeError)):
        pred.label = "paper"  # type: ignore[misc]


def test_classification_result_is_frozen() -> None:
    pred = CategoryPrediction(label="cardboard", confidence=0.9)
    result = ClassificationResult(
        top_prediction=pred,
        alternatives=[pred, pred, pred],
    )
    with pytest.raises((AttributeError, TypeError)):
        result.top_prediction = pred  # type: ignore[misc]
