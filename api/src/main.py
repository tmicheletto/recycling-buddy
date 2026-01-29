"""
FastAPI application for Recycling Buddy
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import logging

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


# Response models
class HealthResponse(BaseModel):
    status: str
    version: str


class PredictionResponse(BaseModel):
    label: str
    confidence: float
    categories: List[Dict[str, float]]


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
        if not file.content_type.startswith("image/"):
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
            ]
        )

    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
