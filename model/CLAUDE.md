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


## Python Development Standards

This section contains critical information about working with this codebase. Follow these guidelines precisely.

### Core Development Rules

1. Package Management
   - ONLY use uv, NEVER pip
   - Installation: `uv add package`
   - Running tools: `uv run tool`
   - Upgrading: `uv add --dev package --upgrade-package package`
   - FORBIDDEN: `uv pip install`, `@latest` syntax

2. Code Quality
   - Type hints required for all code
   - use pyrefly for type checking
     - run `pyrefly init` to start
     - run `pyrefly check` after every change and fix resultings errors
   - Public APIs must have docstrings
   - Functions must be focused and small
   - Follow existing patterns exactly
   - Line length: 88 chars maximum

3. Testing Requirements
   - Framework: `uv run pytest`
   - Async testing: use anyio, not asyncio
   - Coverage: test edge cases and errors
   - New features require tests
   - Bug fixes require regression tests

4. Code Style
    - PEP 8 naming (snake_case for functions/variables)
    - Class names in PascalCase
    - Constants in UPPER_SNAKE_CASE
    - Document with docstrings
    - Use f-strings for formatting

### Development Philosophy

- **Simplicity**: Write simple, straightforward code
- **Readability**: Make code easy to understand
- **Performance**: Consider performance without sacrificing readability
- **Maintainability**: Write code that's easy to update
- **Testability**: Ensure code is testable
- **Reusability**: Create reusable components and functions
- **Less Code = Less Debt**: Minimize code footprint

### Coding Best Practices

- **Early Returns**: Use to avoid nested conditions
- **Descriptive Names**: Use clear variable/function names (prefix handlers with "handle")
- **Constants Over Functions**: Use constants where possible
- **DRY Code**: Don't repeat yourself
- **Functional Style**: Prefer functional, immutable approaches when not verbose
- **Minimal Changes**: Only modify code related to the task at hand
- **Function Ordering**: Define composing functions before their components
- **TODO Comments**: Mark issues in existing code with "TODO:" prefix
- **Simplicity**: Prioritize simplicity and readability over clever solutions
- **Build Iteratively** Start with minimal functionality and verify it works before adding complexity
- **Run Tests**: Test your code frequently with realistic inputs and validate outputs
- **Build Test Environments**: Create testing environments for components that are difficult to validate directly
- **Functional Code**: Use functional and stateless approaches where they improve clarity
- **Clean logic**: Keep core logic clean and push implementation details to the edges
- **File Organsiation**: Balance file organization with simplicity - use an appropriate number of files for the project scale

### Python Tools

- use context7 mcp to check details of libraries

### Code Formatting

1. Ruff
   - Format: `uv run ruff format .`
   - Check: `uv run ruff check .`
   - Fix: `uv run ruff check . --fix`
   - Critical issues:
     - Line length (88 chars)
     - Import sorting (I001)
     - Unused imports
   - Line wrapping:
     - Strings: use parentheses
     - Function calls: multi-line with proper indent
     - Imports: split into multiple lines

2. Type Checking
  - run `pyrefly init` to start
  - run `pyrefly check` after every change and fix resultings errors
   - Requirements:
     - Explicit None checks for Optional
     - Type narrowing for strings
     - Version warnings can be ignored if checks pass


### Error Resolution

1. CI Failures
   - Fix order:
     1. Formatting
     2. Type errors
     3. Linting
   - Type errors:
     - Get full line context
     - Check Optional types
     - Add type narrowing
     - Verify function signatures

2. Common Issues
   - Line length:
     - Break strings with parentheses
     - Multi-line function calls
     - Split imports
   - Types:
     - Add None checks
     - Narrow string types
     - Match existing patterns

3. Best Practices
   - Check git status before commits
   - Run formatters before type checks
   - Keep changes minimal
   - Follow existing patterns
   - Document public APIs
   - Test thoroughly