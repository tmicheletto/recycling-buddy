# API Component

FastAPI backend service for the Recycling Buddy application.

## Overview

This component provides:
- RESTful API endpoints
- Image upload and processing
- Model inference integration
- CORS configuration for frontend

## Tech Stack

- FastAPI 0.104+
- Uvicorn (ASGI server)
- Pydantic for data validation
- Python 3.11+

## Directory Structure

```
api/
├── src/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── models.py        # Pydantic models (to be added)
│   ├── routes/          # API routes (to be added)
│   └── services/        # Business logic (to be added)
├── tests/               # Unit and integration tests
├── Dockerfile           # Container configuration
└── requirements.txt     # Python dependencies
```

## Setup

```bash
cd api
pip install -r requirements.txt
```

## Development

```bash
# Run locally
uvicorn src.main:app --reload

# Run with Docker
docker build -t recycling-buddy-api .
docker run -p 8000:8000 recycling-buddy-api
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### GET /
Root endpoint returning API status

### GET /health
Health check endpoint

### POST /predict
Upload an image for classification

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: image file

**Response:**
```json
{
  "label": "recyclable",
  "confidence": 0.85,
  "categories": [
    {"recyclable": 0.85},
    {"non-recyclable": 0.10},
    {"compost": 0.05}
  ]
}
```

## Testing

```bash
pytest
```

## Environment Variables

- `MODEL_PATH`: Path to the ML model (default: /app/model)
- `PORT`: Server port (default: 8000)
