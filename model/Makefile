.PHONY: train evaluate promote test

ARTIFACT ?= artifacts/efficientnet_b0_recycling_v1.safetensors
S3_BUCKET ?= recycling-buddy-data

train:
	uv run python -m recbuddy.train \
		--s3-bucket $(S3_BUCKET) \
		--output-dir artifacts/ \
		--epochs 30 \
		--seed 42

evaluate:
	uv run python -m recbuddy.evaluate \
		--artifact $(ARTIFACT) \
		--s3-bucket $(S3_BUCKET) \
		--split test

promote:
	uv run python -m recbuddy.promote \
		--artifact $(ARTIFACT) \
		--s3-bucket $(S3_BUCKET)

test:
	uv run pytest
