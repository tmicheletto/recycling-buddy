# Quick Start - Upload Feature

Quick reference for using the photo upload feature.

## Start Services

**One Command:**
```bash
make run
```

This single command will:
- Start all services (LocalStack, API, UI)
- Initialize S3 bucket
- Show service URLs and logs

**Stop Services:**
```bash
make stop
```

## Upload Image

```bash
# Convert image to base64
IMAGE_B64=$(base64 -i your-photo.jpg)

# Upload as recyclable
curl -X POST http://localhost:8000/upload \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"$IMAGE_B64\", \"label\": \"recyclable\"}"

# Upload as not recyclable
curl -X POST http://localhost:8000/upload \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"$IMAGE_B64\", \"label\": \"not_recyclable\"}"
```

## Verify

```bash
# Run full verification
./scripts/verify-upload.sh

# Check S3 contents
aws --endpoint-url=http://localhost:4566 s3 ls s3://recycling-buddy-training/recyclable/
aws --endpoint-url=http://localhost:4566 s3 ls s3://recycling-buddy-training/not_recyclable/

# View API docs
open http://localhost:8000/docs
```

## Run Tests

```bash
cd api && uv run pytest tests/test_upload.py -v
```

## API Documentation

Interactive API docs with examples: http://localhost:8000/docs

## Supported Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)

Images are validated by magic bytes, not file extension.

## Valid Labels

- `recyclable` - Item is recyclable
- `not_recyclable` - Item is not recyclable

## Example Response

```json
{
  "success": true,
  "s3_key": "recyclable/a1b2c3d4-5678-90ab-cdef-1234567890ab_20260130_123456.jpeg",
  "label": "recyclable"
}
```

## Troubleshooting

**"Unable to locate credentials" error?**

This means AWS credentials aren't set. Use `make run` which handles this automatically, or export them manually:
```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_REGION=us-east-1
export S3_ENDPOINT_URL=http://localhost:4566
```

**LocalStack not running?**
```bash
docker compose up localstack -d
curl http://localhost:4566/_localstack/health
```

**API not responding?**
```bash
curl http://localhost:8000/health
```

**Need AWS CLI for LocalStack?**
```bash
# Install awscli-local
pip install awscli-local
# Use awslocal instead of aws
awslocal s3 ls s3://recycling-buddy-training/
```

## Note on LocalStack

LocalStack Community Edition stores S3 data **in-memory only**:
- ✅ Data persists during the same session
- ❌ Data is lost when you stop LocalStack
- 💡 Just re-upload test images after `make run`

For detailed documentation, see [UPLOAD_FEATURE.md](./UPLOAD_FEATURE.md).
