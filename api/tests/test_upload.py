"""Tests for upload endpoint."""

import base64
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


# Sample image bytes
JPEG_HEADER = b"\xff\xd8\xff\xe0\x00\x10JFIF"
PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def test_upload_valid_jpeg():
    """Test successful upload with valid JPEG image."""
    image_data = JPEG_HEADER + b"\x00" * 100
    encoded = base64.b64encode(image_data).decode()

    with patch("src.main.s3_service.upload_training_image") as mock_upload:
        mock_upload.return_value = "aluminum-can/test-key.jpeg"

        response = client.post(
            "/upload",
            json={"image_base64": encoded, "label": "aluminum-can"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["label"] == "aluminum-can"
        assert "test-key" in data["s3_key"]
        mock_upload.assert_called_once()


def test_upload_valid_png():
    """Test successful upload with valid PNG image."""
    image_data = PNG_HEADER + b"\x00" * 100
    encoded = base64.b64encode(image_data).decode()

    with patch("src.main.s3_service.upload_training_image") as mock_upload:
        mock_upload.return_value = "glass-bottle/test-key.png"

        response = client.post(
            "/upload",
            json={"image_base64": encoded, "label": "glass-bottle"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["label"] == "glass-bottle"


def test_upload_invalid_base64():
    """Test upload with invalid base64 data."""
    response = client.post(
        "/upload",
        json={"image_base64": "not-valid-base64!!!", "label": "aluminum-can"},
    )

    assert response.status_code == 400
    assert "Invalid base64 image data" in response.json()["detail"]


def test_upload_invalid_image_format():
    """Test upload with non-image data."""
    text_data = b"This is just text, not an image"
    encoded = base64.b64encode(text_data).decode()

    response = client.post(
        "/upload",
        json={"image_base64": encoded, "label": "aluminum-can"},
    )

    assert response.status_code == 400
    assert "Invalid image format" in response.json()["detail"]


def test_upload_invalid_label():
    """Test upload with invalid label."""
    image_data = JPEG_HEADER + b"\x00" * 100
    encoded = base64.b64encode(image_data).decode()

    response = client.post(
        "/upload",
        json={"image_base64": encoded, "label": "invalid_label"},
    )

    assert response.status_code == 422  # Pydantic validation error


def test_upload_old_binary_label_rejected():
    """Test that old binary labels are rejected with 422."""
    image_data = JPEG_HEADER + b"\x00" * 100
    encoded = base64.b64encode(image_data).decode()

    for old_label in ["recyclable", "not_recyclable"]:
        response = client.post(
            "/upload",
            json={"image_base64": encoded, "label": old_label},
        )
        assert response.status_code == 422


def test_upload_s3_error():
    """Test upload when S3 fails."""
    image_data = JPEG_HEADER + b"\x00" * 100
    encoded = base64.b64encode(image_data).decode()

    with patch("src.main.s3_service.upload_training_image") as mock_upload:
        mock_upload.side_effect = Exception("S3 connection failed")

        response = client.post(
            "/upload",
            json={"image_base64": encoded, "label": "aluminum-can"},
        )

        assert response.status_code == 500
        assert "Failed to upload image" in response.json()["detail"]
