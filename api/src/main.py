"""
FastAPI application for Recycling Buddy
"""

import base64
import logging
from enum import Enum

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import settings
from src.services.s3 import S3Service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Recycling Buddy API",
    description="API for recycling material classification",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize S3 service
s3_service = S3Service(
    bucket=settings.s3_bucket,
    endpoint_url=settings.s3_endpoint_url,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)


# Enums
class RecyclingLabel(str, Enum):
    """Valid recycling labels."""

    recyclable = "recyclable"
    not_recyclable = "not_recyclable"


# Response models
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


class PredictionResponse(BaseModel):
    """Prediction response."""

    label: str
    confidence: float
    categories: list[dict[str, float]]


class UploadRequest(BaseModel):
    """Upload training image request."""

    image_base64: str  # Base64 encoded image
    label: RecyclingLabel


class UploadResponse(BaseModel):
    """Upload training image response."""

    success: bool
    s3_key: str
    label: str


# Routes
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint"""
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", version="0.1.0")


@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    """
    Classify an uploaded image

    Args:
        file: Image file to classify

    Returns:
        Classification results with label and confidence
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # TODO: Implement model inference
        # For now, return a mock response
        logger.info(f"Received image: {file.filename}")

        return PredictionResponse(
            label="recyclable",
            confidence=0.85,
            categories=[
                {"recyclable": 0.85},
                {"non-recyclable": 0.10},
                {"compost": 0.05},
            ],
        )

    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _is_valid_image(data: bytes) -> bool:
    """Check if bytes represent a valid image (JPEG, PNG, etc.).

    Args:
        data: Image bytes

    Returns:
        True if valid image format, False otherwise
    """
    # JPEG: FF D8 FF
    if data[:3] == b"\xff\xd8\xff":
        return True
    # PNG: 89 50 4E 47
    if data[:4] == b"\x89PNG":
        return True
    return False


@app.post("/upload", response_model=UploadResponse)
async def upload_training_image(request: UploadRequest):
    """Upload a training image with label.

    Args:
        request: JSON body with base64 image and label

    Returns:
        Upload confirmation with S3 key
    """
    # Decode base64 image
    try:
        image_bytes = base64.b64decode(request.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    # Validate it's an image (check magic bytes)
    if not _is_valid_image(image_bytes):
        raise HTTPException(status_code=400, detail="Invalid image format")

    try:
        s3_key = s3_service.upload_training_image(
            data=image_bytes,
            label=request.label.value,
        )
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload image")

    return UploadResponse(
        success=True,
        s3_key=s3_key,
        label=request.label.value,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
