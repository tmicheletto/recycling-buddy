"""Promote a trained model artifact to S3.

Uploads under two S3 keys:
  - artifacts/efficientnet_b0_recycling_latest.safetensors  (stable, for API)
  - artifacts/efficientnet_b0_recycling_v{N}.safetensors    (versioned, for history)

Also writes artifacts/latest.json with promotion metadata.

Usage:
    uv run python -m recbuddy.promote \
        --artifact artifacts/efficientnet_b0_recycling_v1.safetensors \
        --s3-bucket recycling-buddy-data
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

_LATEST_KEY = "artifacts/efficientnet_b0_recycling_latest.safetensors"
_MANIFEST_KEY = "artifacts/latest.json"


def promote(
    artifact: Path,
    s3_bucket: str,
    s3_endpoint_url: Optional[str] = None,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    region_name: str = "us-east-1",
) -> str:
    """Upload a local artifact to S3 under the stable latest key and a versioned key.

    Args:
        artifact: Path to the local .safetensors file.
        s3_bucket: S3 bucket to upload to.
        s3_endpoint_url: Optional S3 endpoint for LocalStack.
        aws_access_key_id: Optional AWS access key.
        aws_secret_access_key: Optional AWS secret key.
        region_name: AWS region.

    Returns:
        The stable latest S3 key.
    """
    artifact = Path(artifact)
    if not artifact.exists():
        raise FileNotFoundError(f"Artifact not found: {artifact}")

    client = boto3.client(
        "s3",
        endpoint_url=s3_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name,
    )

    versioned_key = f"artifacts/{artifact.name}"

    logger.info("Uploading to s3://%s/%s", s3_bucket, _LATEST_KEY)
    client.upload_file(str(artifact), s3_bucket, _LATEST_KEY)

    if versioned_key != _LATEST_KEY:
        logger.info("Uploading to s3://%s/%s", s3_bucket, versioned_key)
        client.upload_file(str(artifact), s3_bucket, versioned_key)

    # Derive version from filename, e.g. efficientnet_b0_recycling_v2 -> "v2"
    stem = artifact.stem
    raw = stem.rsplit("_v", 1)[-1] if "_v" in stem else stem
    version = f"v{raw}" if raw.isdigit() else raw

    manifest = {
        "version": version,
        "artifact_key": versioned_key,
        "latest_key": _LATEST_KEY,
        "promoted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    client.put_object(
        Bucket=s3_bucket,
        Key=_MANIFEST_KEY,
        Body=json.dumps(manifest, indent=2).encode(),
        ContentType="application/json",
    )
    logger.info("Manifest written to s3://%s/%s", s3_bucket, _MANIFEST_KEY)
    logger.info("Promoted: %s -> s3://%s/%s", artifact, s3_bucket, _LATEST_KEY)

    return _LATEST_KEY


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote a trained model artifact to S3."
    )
    parser.add_argument("--artifact", required=True, help="Local .safetensors file")
    parser.add_argument("--s3-bucket", required=True, help="Target S3 bucket")
    parser.add_argument(
        "--s3-endpoint-url", default=None, help="S3 endpoint URL (for LocalStack)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()
    key = promote(
        artifact=Path(args.artifact),
        s3_bucket=args.s3_bucket,
        s3_endpoint_url=args.s3_endpoint_url,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    print(f"Promoted to s3://{args.s3_bucket}/{key}")
