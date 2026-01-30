# Recycling Buddy

An ML-powered recycling classification system to help identify recyclable materials from images.

## Architecture

This is a monorepo containing three main components:

```
recycling-buddy/
├── model/      # ML model for image classification
├── api/        # FastAPI backend service
├── ui/         # React frontend
└── shared/     # Shared types and utilities
```

## Tech Stack

- **Model**: Image classification (framework TBD - PyTorch/TensorFlow/scikit-learn)
- **API**: FastAPI with async support
- **UI**: React with TypeScript (Vite)
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose

### Setup

```bash
# Install all dependencies
make setup

# Run all services in development mode
make dev
```

### Development Commands

```bash
make setup           # Install dependencies for all components
make run             # Run all services (LocalStack + API + UI)
make dev             # Run all services with rebuild
make init-localstack # Initialize LocalStack S3 bucket
make stop            # Stop all running services
make logs            # Show logs from running services
make test            # Run tests for all components
make clean           # Clean build artifacts
```

### Quick Start

Run the entire application with one command:

```bash
# Start all services
make run

# Services will be available at:
# - http://localhost:8000 (API)
# - http://localhost:8000/docs (API documentation)
# - http://localhost:5173 (UI)
# - http://localhost:4566 (LocalStack)
```

See [QUICKSTART_UPLOAD.md](./QUICKSTART_UPLOAD.md) for more details.

## Component Documentation

- [Model Documentation](./model/README.md)
- [API Documentation](./api/README.md)
- [UI Documentation](./ui/README.md)

## Project Structure

```
recycling-buddy/
├── model/
│   ├── src/              # Model training and inference code
│   ├── tests/            # Model tests
│   └── requirements.txt  # Python dependencies
├── api/
│   ├── src/              # FastAPI application
│   ├── tests/            # API tests
│   ├── Dockerfile        # API container
│   └── requirements.txt  # Python dependencies
├── ui/
│   ├── src/              # React application
│   ├── public/           # Static assets
│   └── Dockerfile        # UI container
├── shared/
│   └── types/            # Shared type definitions
└── docker-compose.yml    # Service orchestration
```

## License

MIT
