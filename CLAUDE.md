# CLAUDE.md

This file provides guidance to Claude Code when working with the Recycling Buddy monorepo.

## Project Overview

Recycling Buddy is an ML-powered image classification system for identifying recyclable materials. This is a portfolio/showcase project demonstrating end-to-end ML system development.

**Purpose**: Help users identify whether materials are recyclable, non-recyclable, or compostable by uploading images.

## Monorepo Structure

```
recycling-buddy/
├── model/          # ML image classification component
├── api/            # FastAPI backend service
└── ui/             # React frontend
```

Each component has its own `CLAUDE.md` with component-specific guidance:
- See `model/CLAUDE.md` for ML model development
- See `api/CLAUDE.md` for API development
- See `ui/CLAUDE.md` for UI development

## Tech Stack

- **Model**: Image classification (ML framework TBD - PyTorch/TensorFlow/scikit-learn)
- **API**: FastAPI (Python 3.11+) with async support
- **UI**: React 18 + TypeScript, built with Vite
- **Infrastructure**: Docker Compose for local development

## Architecture

### Data Flow

1. User uploads image via React UI
2. UI sends image to FastAPI `/predict` endpoint
3. API processes image and calls ML model for inference
4. API returns classification results to UI
5. UI displays results and recycling guidance

### Component Interactions

- **UI → API**: REST API calls (fetch/axios)
- **API → Model**: Python imports (model loaded in API process)

## Development Workflow

### Initial Setup

```bash
# Install all dependencies
make setup

# Or manually:
cd model && pip install -r requirements.txt
cd ../api && pip install -r requirements.txt
cd ../ui && npm install
```

### Running Services

```bash
# Run all services with Docker Compose
make dev

# Or run individually:
cd api && uvicorn src.main:app --reload        # Port 8000
cd ui && npm run dev                            # Port 5173
```

### Testing

```bash
# Run all tests
make test

# Or test individually:
cd model && pytest
cd api && pytest
cd ui && npm test
```

### Code Quality

- **Python**: Use pytest for testing, follow PEP 8
- **TypeScript**: ESLint configured, use TypeScript strict mode
- **Git**: Commit messages should be descriptive and follow conventional commits

## Key Development Principles

1. **Type Safety**: Use TypeScript in UI, Pydantic models in API
2. **Documentation**: Update README.md files when adding features
4. **Testing**: Write tests for new endpoints and components
5. **Docker First**: Ensure changes work in Docker environment

## Common Tasks

### Adding a New API Endpoint

1. Add route in `api/src/main.py` or create in `api/src/routes/`
2. Define Pydantic request/response models
3. Update `ui/src/types/` with TypeScript equivalents
4. Add tests in `api/tests/`
5. Update `api/README.md` with endpoint documentation

### Adding ML Model Functionality

1. Implement in `model/src/`
2. Update `model/requirements.txt` if new dependencies needed
3. Add integration in `api/src/main.py` for inference
4. Test with sample images
5. Document in `model/README.md`

### Adding UI Components

1. Create component in `ui/src/components/`
2. Use types from `ui/src/types/`
3. Add tests in `ui/src/__tests__/` (when test setup complete)
4. Update `ui/README.md` if significant feature

## Environment Variables

Each component may have its own `.env` file:
- `api/.env`: Model paths, API keys
- `ui/config/.env.dev`: API URL (`API_URL`)

Never commit `.env` files (already in `.gitignore`).

## Troubleshooting

### Docker Issues
- Run `make clean` to remove build artifacts
- Try `docker-compose down -v && docker-compose up --build`

### Port Conflicts
- API: Default port 8000 (configurable in docker-compose.yml)
- UI: Default port 5173 (configurable in vite.config.ts)

### Python Import Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` in the component directory

## Project Goals

This is a portfolio project optimized for:
- **Demonstrating technical skills** across ML, backend, and frontend
- **Clean architecture** and code organization
- **Production-ready patterns** (Docker, testing, documentation)
- **Easy onboarding** for reviewers (clear README, simple setup)

Keep this in mind when making architectural decisions.
