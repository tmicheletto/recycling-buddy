.PHONY: setup dev test clean help run stop logs init-localstack check-docker

# Docker compose command (try plugin first, fallback to standalone)
DOCKER_COMPOSE := $(shell docker compose version > /dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

help:
	@echo "Available commands:"
	@echo "  make setup           - Install dependencies for all components"
	@echo "  make run             - Run all application services (LocalStack + API + UI)"
	@echo "  make dev             - Run all services via Docker Compose"
	@echo "  make init-localstack - Initialize LocalStack S3 bucket"
	@echo "  make stop            - Stop all running services"
	@echo "  make logs            - Show logs from running services"
	@echo "  make test            - Run tests for all components"
	@echo "  make clean           - Clean build artifacts"

check-docker:
	@command -v docker > /dev/null 2>&1 || { echo "❌ Docker is not installed. Please install Docker first."; exit 1; }
	@docker info > /dev/null 2>&1 || { echo "❌ Docker daemon is not running. Please start Docker."; exit 1; }

setup:
	@echo "Setting up model dependencies..."
	cd model && pip install -r requirements.txt
	@echo "Setting up API dependencies..."
	cd api && uv sync
	@echo "Setting up UI dependencies..."
	cd ui && npm install
	@echo "Setup complete!"

run: check-docker
	@echo "🚀 Starting Recycling Buddy - All Services"
	@echo ""
	@echo "Starting services with Docker Compose..."
	@$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "⏳ Waiting for LocalStack to be ready..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -s http://localhost:4566/_localstack/health > /dev/null 2>&1; then \
			echo "✅ LocalStack is ready!"; \
			break; \
		fi; \
		if [ $$i -eq 10 ]; then \
			echo "❌ LocalStack failed to start"; \
			exit 1; \
		fi; \
		sleep 2; \
	done
	@echo ""
	@echo "Creating S3 bucket..."
	@if command -v aws > /dev/null 2>&1; then \
		aws --endpoint-url=http://localhost:4566 s3 mb s3://recycling-buddy-training 2>/dev/null || echo "Bucket already exists"; \
	else \
		echo "⚠️  AWS CLI not found. Install with: brew install awscli"; \
		echo "   Bucket creation skipped - upload endpoint may not work until bucket is created"; \
	fi
	@echo ""
	@echo "✅ All services started!"
	@echo ""
	@echo "📍 Service URLs:"
	@echo "   API:          http://localhost:8000"
	@echo "   API Docs:     http://localhost:8000/docs"
	@echo "   UI:           http://localhost:5173"
	@echo "   LocalStack:   http://localhost:4566"
	@echo ""
	@echo "📋 Useful commands:"
	@echo "   View logs:    make logs"
	@echo "   Stop all:     make stop"
	@echo ""
	@echo "Tailing logs (Ctrl+C to exit)..."
	@$(DOCKER_COMPOSE) logs -f

init-localstack: check-docker
	@echo "Initializing LocalStack..."
	@$(DOCKER_COMPOSE) up localstack -d
	@echo "Waiting for LocalStack..."
	@for i in 1 2 3 4 5; do \
		if curl -s http://localhost:4566/_localstack/health > /dev/null 2>&1; then \
			break; \
		fi; \
		sleep 2; \
	done
	@echo "Creating S3 bucket..."
	@if command -v aws > /dev/null 2>&1; then \
		aws --endpoint-url=http://localhost:4566 s3 mb s3://recycling-buddy-training 2>/dev/null || echo "Bucket already exists"; \
	else \
		echo "❌ AWS CLI not found. Install with: brew install awscli"; \
		exit 1; \
	fi
	@echo "✅ LocalStack initialized!"

stop:
	@echo "Stopping services..."
	@$(DOCKER_COMPOSE) down 2>/dev/null || true
	@pkill -f "uvicorn src.main:app" 2>/dev/null || true
	@echo "✅ Services stopped"

logs:
	@echo "Showing logs (Ctrl+C to exit)..."
	@$(DOCKER_COMPOSE) logs -f

dev: check-docker
	@echo "Starting all services with rebuild..."
	@$(DOCKER_COMPOSE) up --build

test:
	@echo "Running model tests..."
	cd model && pytest || true
	@echo "Running API tests..."
	cd api && uv run pytest
	@echo "Running UI tests..."
	cd ui && npm test || true
	@echo "All tests complete!"

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaning LocalStack data..."
	rm -rf localstack-data 2>/dev/null || true
	@echo "Clean complete!"
