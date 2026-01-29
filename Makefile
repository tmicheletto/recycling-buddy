.PHONY: setup dev test clean help

help:
	@echo "Available commands:"
	@echo "  make setup    - Install dependencies for all components"
	@echo "  make dev      - Run all services in development mode"
	@echo "  make test     - Run tests for all components"
	@echo "  make clean    - Clean build artifacts"

setup:
	@echo "Setting up model dependencies..."
	cd model && pip install -r requirements.txt
	@echo "Setting up API dependencies..."
	cd api && pip install -r requirements.txt
	@echo "Setting up UI dependencies..."
	cd ui && npm install
	@echo "Setup complete!"

dev:
	@echo "Starting all services..."
	docker-compose up --build

test:
	@echo "Running model tests..."
	cd model && pytest
	@echo "Running API tests..."
	cd api && pytest
	@echo "Running UI tests..."
	cd ui && npm test
	@echo "All tests complete!"

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	@echo "Clean complete!"
