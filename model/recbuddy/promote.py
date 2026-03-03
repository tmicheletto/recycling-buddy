"""Promote a trained model artifact to S3.

Uploads to a versioned prefix:
  artifacts/{version}/model.safetensors
  artifacts/{version}/manifest.json

The version is read from pyproject.toml (semver). Errors if the version
already exists in S3 — bump the version in pyproject.toml first.

Usage:
    uv run python -m recbuddy.promote \
        --artifact artifacts/model.safetensors \
        --s3-bucket recycling-buddy-data
"""

import argparse
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

_PYPROJECT_PATH = Path(__file__).parent.parent / "pyproject.toml"


def _read_version(pyproject_path: Path | None = None) -> str:
    """Read the version string from pyproject.toml."""
    import tomllib

    path = pyproject_path or _PYPROJECT_PATH
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def _find_training_metadata(artifact_dir: Path) -> dict | None:
    """Find the most recent training_run_*.json sidecar in artifact_dir."""
    candidates = sorted(artifact_dir.glob("training_run_*.json"), reverse=True)
    if not candidates:
        return None
    return json.loads(candidates[0].read_text())


def _git_sha() -> str | None:
    """Return short git SHA of HEAD, or None if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def promote(
    artifact: Path,
    s3_bucket: str,
    version: str | None = None,
    s3_endpoint_url: Optional[str] = None,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    region_name: str = "us-east-1",
) -> str:
    """Upload a local artifact to a versioned S3 prefix with manifest.

    Args:
        artifact: Path to the local model.safetensors file.
        s3_bucket: S3 bucket to upload to.
        version: Semver string. If None, read from pyproject.toml.
        s3_endpoint_url: Optional S3 endpoint for LocalStack.
        aws_access_key_id: Optional AWS access key.
        aws_secret_access_key: Optional AWS secret key.
        region_name: AWS region.

    Returns:
        The full S3 URI of the uploaded artifact.

    Raises:
        FileNotFoundError: If artifact does not exist.
        ValueError: If the version already exists in S3.
    """
    artifact = Path(artifact)
    if not artifact.exists():
        raise FileNotFoundError(f"Artifact not found: {artifact}")

    if version is None:
        version = _read_version()

    client = boto3.client(
        "s3",
        endpoint_url=s3_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name,
    )

    prefix = f"artifacts/{version}/"
    existing = client.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)
    if existing.get("Contents"):
        raise ValueError(
            f"Version {version} already exists in s3://{s3_bucket}/{prefix}. "
            "Bump the version in pyproject.toml before promoting."
        )

    artifact_key = f"{prefix}model.safetensors"
    logger.info("Uploading to s3://%s/%s", s3_bucket, artifact_key)
    client.upload_file(str(artifact), s3_bucket, artifact_key)

    training_meta = _find_training_metadata(artifact.parent)
    manifest = {
        "version": version,
        "artifact_key": artifact_key,
        "training": {
            "epochs": training_meta.get("epochs") if training_meta else None,
            "val_accuracy": (
                training_meta.get("val_accuracy") if training_meta else None
            ),
            "seed": training_meta.get("seed") if training_meta else None,
            "num_classes": training_meta.get("num_classes") if training_meta else None,
        },
        "promotion": {
            "promoted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "promoted_by": os.environ.get("USER", "unknown"),
            "git_sha": _git_sha(),
        },
    }

    manifest_key = f"{prefix}manifest.json"
    client.put_object(
        Bucket=s3_bucket,
        Key=manifest_key,
        Body=json.dumps(manifest, indent=2).encode(),
        ContentType="application/json",
    )
    logger.info("Manifest written to s3://%s/%s", s3_bucket, manifest_key)

    uri = f"s3://{s3_bucket}/{artifact_key}"
    logger.info("Promoted: %s -> %s", artifact, uri)
    return uri


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote a trained model artifact to S3."
    )
    parser.add_argument(
        "--artifact",
        required=True,
        help="Local model.safetensors file",
    )
    parser.add_argument("--s3-bucket", required=True, help="Target S3 bucket")
    parser.add_argument(
        "--s3-endpoint-url", default=None, help="S3 endpoint URL (for LocalStack)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args()
    uri = promote(
        artifact=Path(args.artifact),
        s3_bucket=args.s3_bucket,
        s3_endpoint_url=args.s3_endpoint_url,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    print(f"Promoted to {uri}")
