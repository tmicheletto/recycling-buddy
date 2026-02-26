# Feature Specification: Waste Item Image Classifier

**Feature Branch**: `001-waste-item-classifier`
**Created**: 2026-02-25
**Status**: Draft
**Input**: User description: "Create a multiclass classifier model that takes an image of a household waste item as input and predicts the category of the item as defined in api/src/labels.py"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Classify a Waste Item from an Image (Priority: P1)

A developer or end-user submits a photo of a household waste item and receives a predicted category label drawn from the 67 defined waste categories, along with a confidence score.

**Why this priority**: This is the core deliverable — without the ability to perform inference, nothing else in the system is useful. Every other story depends on or builds on this capability.

**Independent Test**: Can be fully tested by submitting a sample waste item image and verifying the returned label is one of the 67 defined categories with an associated confidence score.

**Acceptance Scenarios**:

1. **Given** a clear photograph of a glass bottle, **When** the image is submitted for classification, **Then** the system returns `glass-bottles-jars` as the predicted label with a confidence score between 0 and 1.
2. **Given** a photograph of a flattened cardboard box, **When** the image is submitted, **Then** the returned label is `cardboard` and the top-3 predictions all include plausible waste categories.
3. **Given** an image in JPEG, PNG, or WEBP format, **When** submitted for classification, **Then** the system processes it successfully regardless of format.
4. **Given** an image that is very dark, blurry, or low resolution, **When** submitted, **Then** the system returns a prediction with a notably lower confidence score rather than failing.

---

### User Story 2 - Train the Model on a Labeled Dataset (Priority: P2)

An ML engineer triggers a training run using a labeled dataset of waste item images stored in the project's data store, producing a trained model artifact ready for inference.

**Why this priority**: Training is required to produce the model, but the training pipeline is separable from inference — a pre-trained model artifact can serve Story 1 without re-running training.

**Independent Test**: Can be fully tested by running training on a small subset of labeled images and verifying a model artifact is produced that can perform inference.

**Acceptance Scenarios**:

1. **Given** a labeled dataset of images organized by the 67 waste categories, **When** training is initiated, **Then** it completes without errors and produces a saved model artifact.
2. **Given** a training run completes, **When** the resulting model is evaluated on a held-out validation split, **Then** validation accuracy metrics are reported per category and overall.
3. **Given** a prior model checkpoint exists, **When** training is resumed, **Then** the new run starts from that checkpoint rather than from scratch.

---

### User Story 3 - Evaluate Model Performance (Priority: P3)

An ML engineer runs the model against a labeled test set and receives accuracy, precision, recall, and F1 scores broken down by waste category, to determine whether the model meets quality thresholds before deployment.

**Why this priority**: Evaluation is necessary for release confidence but can be deferred until a candidate model exists. A rough model can be deployed and improved iteratively.

**Independent Test**: Can be fully tested by running evaluation against a fixed labeled test set and verifying structured metrics are produced for all 67 categories.

**Acceptance Scenarios**:

1. **Given** a trained model artifact and a labeled test set, **When** evaluation is run, **Then** per-category and overall accuracy, precision, recall, and F1 scores are reported.
2. **Given** evaluation completes, **When** the results are reviewed, **Then** categories with accuracy below an acceptable threshold are clearly identified.
3. **Given** a confusion matrix is generated, **When** reviewed, **Then** commonly confused category pairs are visible to guide further data collection.

---

### Edge Cases

- What happens when the submitted image contains multiple waste items of different categories? The model returns the category for the most visually prominent item without error.
- What happens when the image contains no recognizable waste item (e.g., a blank wall or a person's face)? The model returns its best-guess label with a low confidence score; the calling system is responsible for deciding how to handle low-confidence predictions.
- What happens when a submitted image is corrupted or is not a valid image file? The system rejects the input with a clear error before attempting classification.
- What happens when a waste category is severely underrepresented in training data? The evaluation report flags that category's per-class accuracy as a known gap.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The model MUST accept a single image as input and return a predicted waste category label drawn exclusively from the 67 categories defined in `api/src/labels.py`.
- **FR-002**: The model MUST return a confidence score (a probability value between 0 and 1) alongside each prediction.
- **FR-003**: The model MUST return the top-3 predicted categories with their associated confidence scores, ordered from highest to lowest confidence.
- **FR-004**: The model MUST accept images in JPEG, PNG, and WEBP formats.
- **FR-005**: The model MUST handle images of arbitrary dimensions and aspect ratios by normalising them internally.
- **FR-006**: The training pipeline MUST accept labeled images organised by category (one directory per label) and produce a serialisable model artifact upon completion.
- **FR-007**: The training pipeline MUST support resuming from a prior checkpoint to enable iterative training.
- **FR-008**: The evaluation pipeline MUST produce per-category and overall accuracy, precision, recall, and F1 scores against a labeled test set.
- **FR-009**: The model artifact MUST be exportable to a format that can be loaded for inference without requiring a full training environment.
- **FR-010**: The model MUST classify all 67 categories; no category may be excluded from prediction scope.
- **FR-011**: The model MUST expose a callable Python function (not a network service or CLI) that accepts an image and returns a prediction, so it can be imported and invoked directly within the API process.
- **FR-012**: Submitted images MUST NOT be persisted to any storage medium. The image is used solely for the duration of a single inference call and discarded immediately afterwards.
- **FR-013**: Each inference call MUST produce a log entry recording the predicted label, confidence score, and timestamp. No image data is included in the log.

### Key Entities

- **WasteImage**: A user-submitted photograph of a household waste item. Key attributes: raw binary content, format (JPEG/PNG/WEBP), dimensions.
- **Prediction**: The model's output for a single image. Key attributes: top predicted label, confidence score, top-3 alternatives with scores.
- **WasteCategory**: One of the 67 predefined labels from `api/src/labels.py`. Immutable — additions or removals require a model retrain.
- **LabeledDataset**: A collection of images partitioned into train, validation, and test splits, each image associated with one WasteCategory.
- **ModelArtifact**: A serialised, versioned snapshot of a trained model. Key attributes: version identifier, training date, validation accuracy summary.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The model achieves at least 80% top-1 accuracy on the held-out test set across all 67 categories.
- **SC-002**: The model achieves at least 95% top-3 accuracy on the held-out test set (correct label appears in the top 3 predictions).
- **SC-003**: No individual waste category achieves less than 60% top-1 accuracy on the test set — the model must be useful across all categories, not just common ones.
- **SC-004**: A single image is classified in under 2 seconds on standard server hardware without requiring specialised accelerators.
- **SC-005**: A training run over the full labeled dataset (50–500 images per category, 67 categories) completes within 24 hours on available compute.
- **SC-006**: The model artifact can be loaded and produce its first inference result within 10 seconds of startup.
- **SC-007**: Prediction logs provide sufficient signal to identify the 10 lowest-confidence categories in production within 30 days of deployment, enabling targeted data collection for retraining.
- **SC-008**: The system maintains under 2 seconds per-image classification time (SC-004) under a load of up to 10 concurrent inference requests.

## Clarifications

### Session 2026-02-25

- Q: How does the API service call the classifier model at runtime? → A: In-process function call — model loaded into API process, called as a library.
- Q: Are images submitted for inference stored anywhere, or discarded immediately after the prediction is returned? → A: Discard immediately — image is not stored; only the prediction result is returned.
- Q: Roughly how many labeled training images are available per category? → A: 50–500 per category (moderate dataset, ~3,350–33,500 images total across 67 categories).
- Q: Should individual predictions (label + confidence score, no image) be logged for analysis and future retraining prioritisation? → A: Yes — log predicted label and confidence score per request (no image stored).
- Q: How many concurrent inference requests must the system support without degradation? → A: Low concurrency — 2–10 simultaneous requests.

## Assumptions

- Labeled training images are stored in the project's existing data store (S3), organised using the label strings from `api/src/labels.py` as directory prefixes — consistent with the S3-safe naming convention already enforced by that file.
- The model performs single-image inference (not batch). Batch support, if needed, is a separate feature.
- The calling service (API) is responsible for deciding what to do with low-confidence predictions (e.g., prompting the user to retake the photo). The model always returns its best prediction and a confidence score.
- The 67 categories are fixed at training time. Adding or removing categories requires retraining from scratch.
- No real-time retraining or online learning is required at this stage.
- Images submitted for inference are already captured (not streamed from video).
- The model is integrated as an in-process library — not a separate HTTP service or CLI tool. The API imports and calls the classifier directly, eliminating network overhead and simplifying deployment.
- The system is designed for low concurrency: up to 10 simultaneous inference requests. No distributed inference infrastructure is required at this stage.
- Images submitted for inference are not stored. They are discarded immediately after the prediction is returned. No raw image data persists beyond the lifetime of a single inference call.
- The labeled training dataset is expected to contain 50–500 images per category (~3,350–33,500 images total across 67 categories). Data augmentation is expected to be a necessary part of the training pipeline to compensate for moderate dataset size.
