# Photo Upload Feature

This document describes the photo upload feature for collecting training data.

## Overview

The `/upload` endpoint accepts waste item photos with binary labels (recyclable/not_recyclable) and stores them to AWS S3 for future model training.

## Architecture

### API Design

- **Protocol**: REST API with JSON only
- **Request**: JSON body with base64-encoded image and label
- **Response**: JSON with upload confirmation and S3 key
- **Documentation**: Auto-generated Swagger UI at `/docs`

### Storage Structure

Images are stored in S3 with the following structure:

```
s3://recycling-buddy-training/
├── recyclable/
│   ├── {uuid}_{timestamp}.jpg
│   └── ...
└── not_recyclable/
    ├── {uuid}_{timestamp}.jpg
    └── ...
```

This structure allows easy loading for model training with images organized by label.

### Local Development

LocalStack is used for local S3 testing without requiring AWS credentials.

**Note on Data Persistence:**
- LocalStack Community Edition stores S3 **object data in-memory only**
- Uploaded images are accessible during the same Docker session
- When you restart LocalStack, you'll need to re-upload test images
- Bucket configurations persist with `PERSISTENCE=1` setting
- For production, use real AWS S3

## Implementation Details

### Dependencies

Added via `uv`:
- `boto3` - AWS SDK for S3
- `pydantic-settings` - Environment configuration

### Key Components

1. **S3 Service** (`api/src/services/s3.py`)
   - Handles S3 uploads
   - Detects image format from magic bytes
   - Generates unique keys with timestamps

2. **Config Module** (`api/src/config.py`)
   - Loads settings from environment
   - Supports `.env.dev` file for local development

3. **Upload Endpoint** (`api/src/main.py`)
   - Validates base64 input
   - Checks image format (JPEG/PNG)
   - Returns S3 key on success

### Models

```python
class RecyclingLabel(str, Enum):
    recyclable = "recyclable"
    not_recyclable = "not_recyclable"

class UploadRequest(BaseModel):
    image_base64: str  # Base64 encoded image
    label: RecyclingLabel

class UploadResponse(BaseModel):
    success: bool
    s3_key: str
    label: str
```

## Usage

### Starting the Services

**Simple:**
```bash
make run
```

This starts all services:
- LocalStack (S3 mock)
- API server
- UI server
- Initializes S3 bucket

**Stop:**
```bash
make stop
```

**View Logs:**
```bash
make logs
```

### API Request Example

```bash
# Encode image to base64
IMAGE_B64=$(base64 -i photo.jpg)

# Upload with recyclable label
curl -X POST http://localhost:8000/upload \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"$IMAGE_B64\", \"label\": \"recyclable\"}"
```

### Response Example

```json
{
  "success": true,
  "s3_key": "recyclable/a1b2c3d4-5678-90ab-cdef-1234567890ab_20260130_123456.jpeg",
  "label": "recyclable"
}
```

### Interactive Documentation

Visit http://localhost:8000/docs for Swagger UI with:
- Interactive API testing
- Request/response schemas
- Example payloads

## Verification

Run the automated verification script:

```bash
./scripts/verify-upload.sh
```

This script:
1. Checks if API is running
2. Checks if LocalStack is running
3. Creates S3 bucket
4. Tests upload with both labels
5. Verifies files in S3
6. Checks API documentation

## Testing

Run unit tests:

```bash
cd api && uv run pytest tests/test_upload.py -v
```

Test coverage:
- ✅ Valid JPEG upload
- ✅ Valid PNG upload
- ✅ Invalid base64 data
- ✅ Invalid image format
- ✅ Invalid label
- ✅ S3 error handling

## Configuration

### Environment Variables

**Local Development** (`.env.dev`):
```env
S3_BUCKET=recycling-buddy-training
S3_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
```

**Production**:
- Remove `S3_ENDPOINT_URL` to use real AWS S3
- Set real AWS credentials via environment or IAM roles
- Update `S3_BUCKET` to production bucket name

### Docker Compose

The `docker-compose.yml` includes:
- LocalStack service on port 4566
- API service with S3 environment variables
- Network configuration for service communication

## Security Considerations

1. **Input Validation**: Images are validated via magic bytes (not just file extension)
2. **Base64 Encoding**: Handles malformed base64 gracefully
3. **Label Validation**: Pydantic enum ensures only valid labels
4. **Error Handling**: S3 errors don't expose internal details

## Future Enhancements

Potential improvements:
- [ ] Image size limits (e.g., max 10MB)
- [ ] Image format conversion (normalize to JPEG)
- [ ] Metadata storage (user ID, location, timestamp)
- [ ] Batch upload support
- [ ] Signed URLs for direct S3 upload (bypass API)
- [ ] Duplicate detection
- [ ] Rate limiting

## Troubleshooting

### LocalStack Issues

If S3 operations fail:
```bash
# Check LocalStack status
curl http://localhost:4566/_localstack/health

# List buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# Check logs
docker logs $(docker ps -q -f name=localstack)
```

### API Issues

If uploads fail:
```bash
# Check API logs
cd api && uv run uvicorn src.main:app --reload

# Test health endpoint
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

### Permission Issues

**"Unable to locate credentials" error:**
- Use `make run` which sets credentials automatically
- Or export them manually before starting the API:
  ```bash
  export AWS_ACCESS_KEY_ID=test
  export AWS_SECRET_ACCESS_KEY=test
  export AWS_REGION=us-east-1
  ```
- For LocalStack, any values work (we use "test")
- For production, use proper IAM credentials or IAM roles

## Files Modified/Created

| File | Action |
|------|--------|
| `api/pyproject.toml` | Created (uv project) |
| `api/requirements.txt` | Deleted (replaced by pyproject.toml) |
| `api/src/services/__init__.py` | Created |
| `api/src/services/s3.py` | Created |
| `api/src/config.py` | Created |
| `api/src/main.py` | Modified (added upload endpoint) |
| `api/.env.dev` | Created |
| `api/Dockerfile` | Modified (use uv instead of pip) |
| `docker-compose.yml` | Modified (added LocalStack) |
| `scripts/init-localstack.sh` | Created |
| `scripts/verify-upload.sh` | Created |
| `api/tests/test_upload.py` | Created |

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [LocalStack Documentation](https://docs.localstack.cloud/user-guide/aws/s3/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
