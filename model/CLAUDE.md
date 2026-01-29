# Model Component - CLAUDE.md

Guidance for working with the ML model component of Recycling Buddy.

## Component Overview

This component handles image classification for identifying recyclable materials.

**Current Status**: Framework not yet selected. Placeholder structure in place.

## ML Framework Decision

**Options under consideration:**
1. **PyTorch** - Flexible, research-friendly, excellent for custom architectures
2. **TensorFlow/Keras** - Production-ready, good for deployment
3. **scikit-learn** - For simpler classical ML models (if deep learning isn't needed)

**When framework is chosen:**
1. Uncomment appropriate lines in `requirements.txt`
2. Update this CLAUDE.md with framework-specific patterns
3. Add training scripts in `src/train.py`
4. Add inference code in `src/inference.py`

## Directory Structure

```
model/
├── src/
│   ├── __init__.py
│   ├── train.py         # Training pipeline (to be added)
│   ├── inference.py     # Model inference (to be added)
│   ├── preprocess.py    # Data preprocessing (to be added)
│   └── models/          # Model architectures (to be added)
├── tests/               # Unit tests
├── data/                # Dataset (gitignored, to be created)
├── checkpoints/         # Saved models (gitignored, to be created)
├── Dockerfile
├── requirements.txt
└── README.md
```

## Key Principles

1. **Reproducibility**: Pin dependency versions, use random seeds
2. **Experimentation**: Track experiments (consider adding MLflow/Weights&Biases)
3. **Model Versioning**: Save checkpoints with version numbers or timestamps
4. **Data Separation**: Keep training/validation/test splits clear
5. **Inference Optimization**: Consider model size for deployment

## Common Tasks

### Training a New Model

```python
# Typical structure for src/train.py
# - Load and preprocess data
# - Define model architecture
# - Set up training loop with validation
# - Save best checkpoint
# - Log metrics
```

**Important:**
- Save models to `checkpoints/` (gitignored)
- Log training metrics (loss, accuracy, etc.)
- Use validation set to prevent overfitting
- Document hyperparameters

### Running Inference

```python
# Typical structure for src/inference.py
# - Load trained model from checkpoint
# - Preprocess input image
# - Run prediction
# - Return label and confidence scores
```

**Important:**
- Handle various image formats (JPEG, PNG)
- Resize/normalize inputs consistently with training
- Return probabilities for all classes, not just top prediction
- Add error handling for invalid inputs

### Data Preprocessing

**Expected input format:**
- Images of recyclable/non-recyclable/compostable materials
- Consider data augmentation (rotation, flip, crop) during training

**Preprocessing steps:**
- Resize to consistent dimensions
- Normalize pixel values
- Convert to appropriate tensor format

### Model Evaluation

**Metrics to track:**
- Accuracy
- Precision/Recall per class
- Confusion matrix
- F1 score

**Consider:**
- Class imbalance (some recycling categories may be rarer)
- Real-world performance vs. benchmark datasets

## Testing

```bash
cd model
pytest tests/
```

**What to test:**
- Data preprocessing functions
- Model input/output shapes
- Inference with sample images
- Edge cases (corrupted images, wrong formats)

## Integration with API

The API component will import model inference functions:

```python
# In api/src/main.py
from model.src.inference import predict_image

result = predict_image(image_bytes)
```

**Requirements for API integration:**
- Inference function should accept image bytes or PIL Image
- Return dict with `label`, `confidence`, and `categories`
- Handle errors gracefully (return error messages, not crashes)
- Optimize for low latency if possible

## Dataset Considerations

**For recycling classification:**
- Consider using existing datasets (e.g., TrashNet, TACO)
- May need custom data collection
- Label categories: recyclable, non-recyclable, compost (or more granular)

**Data location:**
- Store in `model/data/` (gitignored due to size)
- Document data source and preparation steps in README

## Performance Goals

**Target metrics (adjust based on use case):**
- Accuracy: >85% on validation set
- Inference time: <500ms per image
- Model size: <100MB for deployment

## Common Patterns (will update when framework chosen)

### PyTorch Pattern
```python
# Example structure
import torch
import torch.nn as nn

class RecyclingClassifier(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        # Define architecture

    def forward(self, x):
        # Forward pass
        return x
```

### TensorFlow/Keras Pattern
```python
# Example structure
import tensorflow as tf

model = tf.keras.Sequential([
    # Define layers
])

model.compile(optimizer='adam', loss='categorical_crossentropy')
```

## Troubleshooting

### Out of Memory Errors
- Reduce batch size
- Use gradient accumulation
- Consider smaller model architecture

### Poor Performance
- Check data quality and labels
- Try data augmentation
- Experiment with different architectures
- Adjust learning rate

### Overfitting
- Add dropout layers
- Use data augmentation
- Reduce model complexity
- Add regularization

## Next Steps

1. Choose ML framework based on project requirements
2. Find or create dataset for recycling classification
3. Implement training pipeline
4. Train initial baseline model
5. Integrate with API for inference
6. Iterate on model architecture and hyperparameters
