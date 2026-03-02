"""
FastAPI application for Recycling Buddy
"""

import asyncio
import base64
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.guidelines import AdviceRecord, GuidelinesService
from app.inference import ClassificationModel
from app.labels import ALL_LABELS, ALL_LABELS_LIST
from app.services.s3 import S3Service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise app state; model is loaded lazily on first /predict request."""
    app.state.model = None
    app.state.model_lock = asyncio.Lock()
    app.state.guidelines_service = GuidelinesService()
    yield


# Initialize FastAPI app
app = FastAPI(
    title="Recycling Buddy API",
    description="API for recycling material classification",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
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


class LabelItem(BaseModel):
    """A single label entry."""

    value: str
    display_name: str


class LabelsResponse(BaseModel):
    """Response for GET /labels."""

    items: list[LabelItem]
    total_count: int


class UploadRequest(BaseModel):
    """Upload training image request."""

    image_base64: str  # Base64 encoded image
    label: str

    @field_validator("label")
    @classmethod
    def label_must_be_valid(cls, v: str) -> str:
        if v not in ALL_LABELS:
            raise ValueError(f"Invalid label '{v}'. Use GET /labels for valid options.")
        return v


class UploadResponse(BaseModel):
    """Upload training image response."""

    success: bool
    s3_key: str
    label: str


class AdviceResponse(BaseModel):
    """Response for GET /advice."""

    council_slug: str
    item_category: str
    bin_colour: str
    bin_name: str
    prep_instructions: str
    disposal_method: str
    special_disposal_flag: bool
    notes: str
    is_fallback: bool


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
async def predict(request: Request, file: UploadFile = File(...)) -> PredictionResponse:
    """Classify an uploaded waste item image.

    Args:
        request: FastAPI request (provides access to app.state.model).
        file: Image file to classify (JPEG, PNG, or WEBP).

    Returns:
        PredictionResponse with top label, confidence, and top-3 categories.
    """
    if request.app.state.model is None:
        async with request.app.state.model_lock:
            if request.app.state.model is None:
                try:
                    request.app.state.model = await run_in_threadpool(
                        ClassificationModel.from_artifact,
                        settings.model_artifact_path,
                    )
                    logger.info("Model loaded lazily on first /predict request")
                except Exception as exc:
                    logger.exception("Model failed to load")
                    raise HTTPException(
                        status_code=503,
                        detail="Model artifact not available. Run the training pipeline first.",
                    )
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()

    try:
        result = await run_in_threadpool(request.app.state.model.predict, image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Prediction error: %s", exc)
        raise HTTPException(status_code=500, detail="Inference failed")

    # FR-013: emit structured prediction log (no image data)
    logger.info(
        json.dumps(
            {
                "event": "prediction",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "predicted_label": result.top_prediction.label,
                "confidence": result.top_prediction.confidence,
            }
        )
    )

    return PredictionResponse(
        label=result.top_prediction.label,
        confidence=result.top_prediction.confidence,
        categories=[{pred.label: pred.confidence} for pred in result.alternatives],
    )


def _display_name(label: str) -> str:
    """Convert a label like 'aluminum-can' to 'Aluminum Can'."""
    return label.replace("-", " ").title()


@app.get("/labels", response_model=LabelsResponse)
async def get_labels():
    """Return all valid labels as a flat list."""
    items = [
        LabelItem(value=lbl, display_name=_display_name(lbl)) for lbl in ALL_LABELS_LIST
    ]
    return LabelsResponse(
        items=items,
        total_count=len(items),
    )


@app.get("/advice", response_model=AdviceResponse)
async def get_advice(request: Request, item_category: str, council_slug: str) -> AdviceResponse:
    """Return council-specific bin advice for an item category.

    Args:
        request: FastAPI request (provides access to app.state.guidelines_service).
        item_category: Classifier label (e.g. 'cardboard').
        council_slug: RNY council slug (e.g. 'SydneyNSW').

    Returns:
        AdviceResponse with bin decision and instructions.
    """
    service: GuidelinesService = request.app.state.guidelines_service
    record: AdviceRecord = await service.lookup(item_category, council_slug)
    return AdviceResponse(
        council_slug=record.council_slug,
        item_category=record.item_category,
        bin_colour=record.bin_colour,
        bin_name=record.bin_name,
        prep_instructions=record.prep_instructions,
        disposal_method=record.disposal_method,
        special_disposal_flag=record.special_disposal_flag,
        notes=record.notes,
        is_fallback=record.is_fallback,
    )


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
            label=request.label,
        )
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload image")

    return UploadResponse(
        success=True,
        s3_key=s3_key,
        label=request.label,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
