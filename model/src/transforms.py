"""Image transforms for training and inference.

Uses torchvision.transforms.v2 (the current API).
ImageNet normalisation constants are used for all pretrained torchvision backbones.
"""

import torch
from torchvision.transforms import v2 as T

_IMAGENET_MEAN: list[float] = [0.485, 0.456, 0.406]
_IMAGENET_STD: list[float] = [0.229, 0.224, 0.225]


def inference_transform() -> T.Compose:
    """Return the inference/validation transform pipeline.

    Resize → CenterCrop 224 → float tensor → ImageNet normalise.
    """
    return T.Compose(
        [
            T.Resize(256),
            T.CenterCrop(224),
            T.ToImage(),
            T.ToDtype(torch.float32, scale=True),
            T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
        ]
    )


def training_transform() -> T.Compose:
    """Return the augmented training transform pipeline.

    Applies TrivialAugmentWide (parameter-free, small-dataset-friendly),
    Mixup is applied separately in the training loop.
    """
    return T.Compose(
        [
            T.RandomResizedCrop(224, scale=(0.7, 1.0)),
            T.RandomHorizontalFlip(),
            T.TrivialAugmentWide(),
            T.ToImage(),
            T.ToDtype(torch.float32, scale=True),
            T.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
            T.RandomErasing(p=0.25),
        ]
    )
