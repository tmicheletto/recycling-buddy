"""Integration tests for POST /predict endpoint.

Tests must FAIL before implementation exists (TDD — constitution Principle II).
The model is injected via app.state to avoid loading a real artifact.
"""

import io
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.inference import CategoryPrediction, ClassificationResult
from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_model() -> MagicMock:
    """A mock ClassificationModel that returns a fixed result."""
    mock = MagicMock()
    mock.predict.return_value = ClassificationResult(
        top_prediction=CategoryPrediction(label="cardboard", confidence=0.923),
        alternatives=[
            CategoryPrediction(label="cardboard", confidence=0.923),
            CategoryPrediction(label="plastic-lined-cardboard", confidence=0.041),
            CategoryPrediction(label="paper", confidence=0.018),
        ],
    )
    return mock


@pytest.fixture
def valid_jpeg_bytes() -> bytes:
    """Minimal valid 32×32 JPEG image bytes."""
    img = Image.new("RGB", (32, 32), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def client(mock_model: MagicMock) -> TestClient:
    """TestClient with mock model pre-loaded on app.state (no lifespan)."""
    app.state.model = mock_model
    return TestClient(app)


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_predict_returns_200_with_valid_jpeg(
    client: TestClient, valid_jpeg_bytes: bytes
) -> None:
    response = client.post(
        "/predict",
        files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 200


def test_predict_response_contains_label(
    client: TestClient, valid_jpeg_bytes: bytes
) -> None:
    response = client.post(
        "/predict",
        files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    body = response.json()
    assert "label" in body
    assert body["label"] == "cardboard"


def test_predict_response_confidence_in_unit_interval(
    client: TestClient, valid_jpeg_bytes: bytes
) -> None:
    response = client.post(
        "/predict",
        files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    body = response.json()
    assert 0.0 <= body["confidence"] <= 1.0


def test_predict_response_categories_has_three_entries(
    client: TestClient, valid_jpeg_bytes: bytes
) -> None:
    response = client.post(
        "/predict",
        files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    body = response.json()
    assert len(body["categories"]) == 3


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_predict_returns_400_when_no_file(client: TestClient) -> None:
    response = client.post("/predict")
    assert response.status_code == 422  # FastAPI returns 422 for missing required field


def test_predict_returns_400_for_non_image_content_type(
    client: TestClient,
) -> None:
    response = client.post(
        "/predict",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Privacy: no image written to disk
# ---------------------------------------------------------------------------


def test_predict_does_not_write_image_to_disk(
    client: TestClient, valid_jpeg_bytes: bytes, tmp_path, monkeypatch
) -> None:
    """Verify no image file is created during inference (FR-012)."""
    monkeypatch.chdir(tmp_path)
    client.post(
        "/predict",
        files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
    )
    image_files = list(tmp_path.rglob("*.jpg")) + list(tmp_path.rglob("*.png"))
    assert len(image_files) == 0
