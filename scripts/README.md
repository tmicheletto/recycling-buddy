# Scripts Directory

Utility scripts for the Recycling Buddy project.

## Available Scripts

### verify-upload.sh

Comprehensive verification script for the upload feature.

**Usage:**
```bash
./scripts/verify-upload.sh
```

**Requirements:**
- API running on http://localhost:8000
- LocalStack running on http://localhost:4566
- `curl`, `aws` CLI, `python3`

**What it does:**
1. Checks if API is running
2. Checks if LocalStack is running
3. Creates S3 bucket
4. Creates a test image
5. Tests upload endpoint with both labels
6. Verifies files in S3
7. Checks API documentation

**Output:**
- Success: All checks pass with ✅
- Failure: Exits with error code and ❌ message

## Installation Notes

### AWS Local CLI

For easier LocalStack interaction, install `awslocal`:

```bash
pip install awscli-local
```

Then use `awslocal` instead of `aws --endpoint-url=http://localhost:4566`:

```bash
# Standard AWS CLI with LocalStack
aws --endpoint-url=http://localhost:4566 s3 ls

# Simplified with awslocal
awslocal s3 ls
```

## Makefile Integration

This script can be run as part of the verification process:

```bash
make run    # Automatically sets up LocalStack and S3
./scripts/verify-upload.sh  # Verify the upload feature works
```

For manual LocalStack initialization, use:
```bash
make init-localstack  # Starts LocalStack and creates S3 bucket
```
