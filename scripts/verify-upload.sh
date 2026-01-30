#!/bin/bash
# Verification script for upload endpoint

set -e

echo "=== Upload Feature Verification ==="
echo ""

# Check if API is running
echo "1. Checking if API is running..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ API is not running. Start it with: make run"
    exit 1
fi
echo "✅ API is running"
echo ""

# Check if LocalStack is running
echo "2. Checking if LocalStack is running..."
if ! curl -s http://localhost:4566/_localstack/health > /dev/null 2>&1; then
    echo "❌ LocalStack is not running. Start it with: make init-localstack"
    exit 1
fi
echo "✅ LocalStack is running"
echo ""

# Create S3 bucket
echo "3. Creating S3 bucket..."
aws --endpoint-url=http://localhost:4566 s3 mb s3://recycling-buddy-training 2>/dev/null || echo "Bucket already exists"
echo "✅ Bucket ready"
echo ""

# Create a test image
echo "4. Creating test image..."
TEST_IMAGE=$(mktemp /tmp/test_image.XXXXXX.jpg)
# Create a minimal valid JPEG (1x1 pixel)
printf '\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00\x43\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\x09\x09\x08\x0a\x0c\x14\x0d\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c\x20\x24\x2e\x27\x20\x22\x2c\x23\x1c\x1c\x28\x37\x29\x2c\x30\x31\x34\x34\x34\x1f\x27\x39\x3d\x38\x32\x3c\x2e\x33\x34\x32\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x7f\xff\xd9' > "$TEST_IMAGE"
echo "✅ Test image created at $TEST_IMAGE"
echo ""

# Test upload with recyclable label
echo "5. Testing upload endpoint with 'recyclable' label..."
IMAGE_B64=$(base64 -i "$TEST_IMAGE")
RESPONSE=$(curl -s -X POST http://localhost:8000/upload \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"$IMAGE_B64\", \"label\": \"recyclable\"}")

if echo "$RESPONSE" | grep -q '"success":true'; then
    echo "✅ Upload successful"
    echo "Response: $RESPONSE"
else
    echo "❌ Upload failed"
    echo "Response: $RESPONSE"
    rm "$TEST_IMAGE"
    exit 1
fi
echo ""

# Verify in S3
echo "6. Verifying image in S3..."
S3_KEY=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['s3_key'])")
echo "S3 Key: $S3_KEY"

FILES=$(aws --endpoint-url=http://localhost:4566 s3 ls s3://recycling-buddy-training/recyclable/)
if [ -n "$FILES" ]; then
    echo "✅ File found in S3"
    echo "Files in bucket:"
    echo "$FILES"
else
    echo "❌ File not found in S3"
    rm "$TEST_IMAGE"
    exit 1
fi
echo ""

# Test with not_recyclable label
echo "7. Testing upload with 'not_recyclable' label..."
RESPONSE=$(curl -s -X POST http://localhost:8000/upload \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"$IMAGE_B64\", \"label\": \"not_recyclable\"}")

if echo "$RESPONSE" | grep -q '"success":true'; then
    echo "✅ Upload successful"
else
    echo "❌ Upload failed"
    rm "$TEST_IMAGE"
    exit 1
fi
echo ""

# Check API docs
echo "8. Checking API documentation..."
if curl -s http://localhost:8000/docs | grep -q "FastAPI"; then
    echo "✅ API documentation available at http://localhost:8000/docs"
else
    echo "❌ API documentation not accessible"
fi
echo ""

# Cleanup
rm "$TEST_IMAGE"

echo "=== All Verifications Passed! ==="
echo ""
echo "Next steps:"
echo "- View API docs: http://localhost:8000/docs"
echo "- List S3 files: aws --endpoint-url=http://localhost:4566 s3 ls s3://recycling-buddy-training/recyclable/"
