"""Integration tests for POST /predict endpoint.

Tests must FAIL before implementation exists (TDD — constitution Principle II).
The model is injected via app.state to avoid loading a real artifact.
"""

import asyncio
import io
import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
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


# ---------------------------------------------------------------------------
# Lazy loading
# ---------------------------------------------------------------------------


def test_predict_returns_503_when_model_fails_to_load(
    monkeypatch, valid_jpeg_bytes: bytes
) -> None:
    """503 is returned when the artifact can't be loaded on first /predict."""
    monkeypatch.setattr(app.state, "model", None, raising=False)
    monkeypatch.setattr(app.state, "model_lock", asyncio.Lock(), raising=False)
    with patch(
        "app.main.ClassificationModel.from_artifact",
        side_effect=FileNotFoundError("no artifact"),
    ):
        client = TestClient(app)
        response = client.post(
            "/predict",
            files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
        )
    assert response.status_code == 503


def test_predict_loads_model_lazily_on_first_request(
    monkeypatch, mock_model: MagicMock, valid_jpeg_bytes: bytes
) -> None:
    """Model is loaded from artifact and cached in app.state on first /predict."""
    monkeypatch.setattr(app.state, "model", None, raising=False)
    monkeypatch.setattr(app.state, "model_lock", asyncio.Lock(), raising=False)
    with patch(
        "app.main.ClassificationModel.from_artifact",
        return_value=mock_model,
    ):
        client = TestClient(app)
        response = client.post(
            "/predict",
            files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
        )
    assert response.status_code == 200
    assert app.state.model is mock_model


def test_predict_downloads_artifact_when_path_is_s3_uri(
    monkeypatch, mock_model: MagicMock, valid_jpeg_bytes: bytes
) -> None:
    """When MODEL_ARTIFACT_PATH is an s3:// URI, artifact is downloaded before load."""
    monkeypatch.setattr(app.state, "model", None, raising=False)
    monkeypatch.setattr(app.state, "model_lock", asyncio.Lock(), raising=False)
    monkeypatch.setattr(
        settings,
        "model_artifact_path",
        "s3://recycling-buddy-data/artifacts/efficientnet_b0_recycling_latest.safetensors",
    )
    with (
        patch("app.main.s3_service.download_artifact") as mock_download,
        patch(
            "app.main.ClassificationModel.from_artifact", return_value=mock_model
        ) as mock_from_artifact,
    ):
        client = TestClient(app)
        response = client.post(
            "/predict",
            files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
        )
    assert response.status_code == 200
    mock_download.assert_called_once_with(
        "artifacts/efficientnet_b0_recycling_latest.safetensors",
        "/tmp/model.safetensors",
        bucket="recycling-buddy-data",
    )
    mock_from_artifact.assert_called_once_with("/tmp/model.safetensors")


def test_predict_does_not_download_when_path_is_local(
    monkeypatch, mock_model: MagicMock, valid_jpeg_bytes: bytes
) -> None:
    """When MODEL_ARTIFACT_PATH is a local path, no S3 download is attempted."""
    monkeypatch.setattr(app.state, "model", None, raising=False)
    monkeypatch.setattr(app.state, "model_lock", asyncio.Lock(), raising=False)
    monkeypatch.setattr(
        settings, "model_artifact_path", "/some/local/model.safetensors"
    )
    with (
        patch("app.main.s3_service.download_artifact") as mock_download,
        patch("app.main.ClassificationModel.from_artifact", return_value=mock_model),
    ):
        client = TestClient(app)
        response = client.post(
            "/predict",
            files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
        )
    assert response.status_code == 200
    mock_download.assert_not_called()


def test_predict_logs_model_version_on_load(
    monkeypatch, mock_model: MagicMock, valid_jpeg_bytes: bytes, caplog
) -> None:
    """Model version from artifact path is logged on first load."""
    monkeypatch.setattr(app.state, "model", None, raising=False)
    monkeypatch.setattr(app.state, "model_lock", asyncio.Lock(), raising=False)
    monkeypatch.setattr(
        settings,
        "model_artifact_path",
        "s3://recycling-buddy-data/artifacts/0.2.0/model.safetensors",
    )
    with (
        patch("app.main.s3_service.download_artifact"),
        patch("app.main.ClassificationModel.from_artifact", return_value=mock_model),
        caplog.at_level(logging.INFO),
    ):
        client = TestClient(app)
        client.post(
            "/predict",
            files={"file": ("photo.jpg", valid_jpeg_bytes, "image/jpeg")},
        )
    assert any("0.2.0" in record.message for record in caplog.records)
