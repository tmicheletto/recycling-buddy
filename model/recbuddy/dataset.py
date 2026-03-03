"""Dataset loading and S3 integration for Recycling Buddy training data.

Downloads labeled images from S3 into model/data/ and wraps them as a
torchvision ImageFolder dataset with train/val/test splits.
"""

from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from torch.utils.data import Subset
from torchvision.datasets import ImageFolder

from recbuddy.transforms import inference_transform, training_transform


class WasteDataset:
    """Downloads labeled waste images from S3 and provides train/val/test splits.

    S3 structure expected: ``<bucket>/<label>/<filename>.<ext>``
    Local mirror: ``data/<label>/<filename>.<ext>``

    Args:
        s3_bucket: Name of the S3 bucket containing labeled images.
        data_dir: Local directory for the downloaded image cache.
        endpoint_url: Optional S3 endpoint URL (for LocalStack in dev).
        aws_access_key_id: Optional AWS access key.
        aws_secret_access_key: Optional AWS secret key.
        region_name: AWS region.
    """

    def __init__(
        self,
        s3_bucket: str,
        data_dir: str = "data",
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
    ) -> None:
        self.s3_bucket = s3_bucket
        self.data_dir = Path(data_dir)
        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )

    def download(self) -> None:
        """Download all labeled images from S3 to ``data_dir``.

        Skips files that already exist locally (idempotent).
        Structure: ``data/<label>/<filename>``
        """
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.s3_bucket):
            for obj in page.get("Contents", []):
                key: str = obj["Key"]
                local_path = self.data_dir / key
                if local_path.exists():
                    continue
                local_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    self._s3.download_file(self.s3_bucket, key, str(local_path))
                except ClientError as exc:
                    raise RuntimeError(
                        f"Failed to download s3://{self.s3_bucket}/{key}"
                    ) from exc

    def get_splits(
        self,
        val_frac: float = 0.15,
        test_frac: float = 0.15,
        seed: int = 42,
    ) -> tuple[Subset, Subset, Subset]:
        """Return (train, val, test) datasets derived from the downloaded images.

        Args:
            val_frac: Fraction of images reserved for validation.
            test_frac: Fraction of images reserved for testing.
            seed: Random seed for reproducible splits.

        Returns:
            Tuple of (train_dataset, val_dataset, test_dataset).

        Raises:
            FileNotFoundError: If ``data_dir`` is empty or does not exist.
        """
        if not self.data_dir.exists() or not any(self.data_dir.iterdir()):
            raise FileNotFoundError(
                f"No data found at {self.data_dir}. Run download() first."
            )

        # Build the full dataset with inference transforms (split after)
        full_dataset = ImageFolder(
            root=str(self.data_dir),
            transform=inference_transform(),
        )

        n = len(full_dataset)
        n_val = int(n * val_frac)
        n_test = int(n * test_frac)
        n_train = n - n_val - n_test

        import torch

        generator = torch.Generator().manual_seed(seed)
        train_ds, val_ds, test_ds = torch.utils.data.random_split(
            full_dataset,
            [n_train, n_val, n_test],
            generator=generator,
        )

        # Override transform on training subset to use augmented pipeline
        train_ds.dataset = ImageFolder(
            root=str(self.data_dir),
            transform=training_transform(),
        )

        return train_ds, val_ds, test_ds

    @property
    def class_to_idx(self) -> dict[str, int]:
        """Return the label → class index mapping from the ImageFolder."""
        ds = ImageFolder(root=str(self.data_dir))
        return ds.class_to_idx
