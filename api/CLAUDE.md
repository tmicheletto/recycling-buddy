# API Component - CLAUDE.md

Guidance for working with the FastAPI backend component of Recycling Buddy.

## Component Overview

FastAPI service providing REST endpoints for the Recycling Buddy application.

**Current Status**: Basic structure with health check and mock prediction endpoint.

## Tech Stack

- **Framework**: FastAPI 0.104+
- **Server**: Uvicorn (ASGI)
- **Validation**: Pydantic v2
- **Python**: 3.11+
- **Testing**: pytest with httpx

## Directory Structure

```
api/
├── src/
│   ├── __init__.py
│   ├── main.py          # FastAPI app and routes
│   ├── models.py        # Pydantic models (to be added)
│   ├── routes/          # Organized routes (to be added)
│   ├── services/        # Business logic (to be added)
│   └── config.py        # Configuration (to be added)
├── tests/
│   └── __init__.py
├── Dockerfile
├── requirements.txt
└── README.md
```

## Current Endpoints

### GET /
Root endpoint returning API status

### GET /health
Health check for monitoring

### POST /predict
Image classification endpoint
- **Input**: multipart/form-data with image file
- **Output**: JSON with label, confidence, and category scores
- **Current**: Returns mock data (needs model integration)

## Key Principles

1. **Type Safety**: Use Pydantic models for all request/response data
2. **Async First**: Use async/await for I/O operations
3. **Error Handling**: Return appropriate HTTP status codes
4. **CORS**: Configured for localhost:5173 (React dev server)
5. **Documentation**: FastAPI auto-generates OpenAPI docs at `/docs`

## Common Tasks

### Adding a New Endpoint

1. **Define Pydantic models** (request/response):
```python
from pydantic import BaseModel

class NewRequest(BaseModel):
    field: str

class NewResponse(BaseModel):
    result: str
```

2. **Add route**:
```python
@app.post("/new-endpoint", response_model=NewResponse)
async def new_endpoint(request: NewRequest):
    # Implementation
    return NewResponse(result="success")
```

3. **Update shared types** in `../shared/types/` with TypeScript equivalent

4. **Add tests** in `tests/test_endpoints.py`

### Organizing Routes

As the API grows, split routes into separate files:

```python
# src/routes/prediction.py
from fastapi import APIRouter

router = APIRouter(prefix="/predict", tags=["prediction"])

@router.post("/")
async def predict_image():
    ...

# src/main.py
from src.routes import prediction
app.include_router(prediction.router)
```

### Integrating the ML Model

**Steps:**
1. Import model inference from `../model/src/inference.py`
2. Load model once at startup (not per request)
3. Call model in `/predict` endpoint

**Example:**
```python
from model.src.inference import load_model, predict_image

# Global model instance
model = None

@app.on_event("startup")
async def startup_event():
    global model
    model = load_model("path/to/checkpoint")

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = predict_image(model, image_bytes)
    return result
```

### File Upload Handling

**Current implementation** accepts images via multipart/form-data.

**Best practices:**
- Validate content type (must be image/*)
- Limit file size (add `max_size` validation)
- Handle corrupt/invalid images gracefully
- Clean up temp files if needed

**Example validation:**
```python
from fastapi import HTTPException

if not file.content_type.startswith("image/"):
    raise HTTPException(status_code=400, detail="File must be an image")

# Optional: Check file size
contents = await file.read()
if len(contents) > 10 * 1024 * 1024:  # 10MB limit
    raise HTTPException(status_code=400, detail="File too large")
```

### Error Handling

**Use appropriate HTTP status codes:**
- 200: Success
- 400: Bad request (invalid input)
- 404: Not found
- 422: Validation error (Pydantic handles automatically)
- 500: Internal server error

**Example:**
```python
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        # Process image
        result = process_image(file)
        return result
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Configuration

**Environment variables** (create `api/.env`):
```
MODEL_PATH=/path/to/model/checkpoint
API_PORT=8000
LOG_LEVEL=INFO
```

**Loading config:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_path: str = "/app/model"
    api_port: int = 8000
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

## CORS Configuration

**Current setup** allows requests from `http://localhost:5173` (React dev).

**For production**, update allowed origins:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing

```bash
cd api
pytest tests/ -v
```

**Test structure:**
```python
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_predict_endpoint():
    with open("test_image.jpg", "rb") as f:
        response = client.post(
            "/predict",
            files={"file": ("test.jpg", f, "image/jpeg")}
        )
    assert response.status_code == 200
    assert "label" in response.json()
```

## Running Locally

```bash
# Development mode with auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# With Docker
docker build -t recycling-buddy-api .
docker run -p 8000:8000 recycling-buddy-api
```

**Access documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Performance Considerations

1. **Model loading**: Load once at startup, not per request
2. **Async operations**: Use async for file I/O and external calls
3. **Connection pooling**: If using database, configure pool size
4. **Caching**: Consider caching frequent predictions (if applicable)

## Security Best Practices

1. **Input validation**: Always validate file uploads
2. **Rate limiting**: Add rate limiting for production (e.g., slowapi)
3. **CORS**: Restrict origins in production
4. **HTTPS**: Use HTTPS in production
5. **Secrets**: Never commit API keys or secrets (use environment variables)

## Shared Types

**Keep `../shared/types/prediction.ts` in sync with Pydantic models.**

**Example Pydantic model:**
```python
class PredictionResponse(BaseModel):
    label: str
    confidence: float
    categories: List[Dict[str, float]]
```

**Corresponding TypeScript:**
```typescript
export interface PredictionResponse {
  label: string;
  confidence: number;
  categories: CategoryScore[];
}
```

## Common Issues

### Import Errors from Model
- Ensure `../model` is in Python path
- May need to adjust `sys.path` or use relative imports
- Consider making model a proper package

### CORS Errors
- Check allowed origins in middleware
- Ensure credentials handling is consistent
- Verify preflight (OPTIONS) requests work

### File Upload Issues
- Check content-type headers
- Verify multipart/form-data encoding
- Test with various image formats

## Next Steps

1. Integrate real ML model inference (replace mock response)
2. Add input validation and file size limits
3. Implement proper error handling and logging
4. Add database if needed (user history, feedback)
5. Consider adding authentication if required
6. Set up monitoring and metrics
