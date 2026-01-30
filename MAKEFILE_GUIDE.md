# Makefile Guide

Comprehensive guide to using the Makefile for Recycling Buddy development.

## Quick Reference

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make setup` | Install dependencies for all components |
| `make run` | **Run all application services** |
| `make dev` | Run all services with rebuild |
| `make init-localstack` | Initialize LocalStack S3 bucket |
| `make stop` | Stop all running services |
| `make logs` | Show logs from running services |
| `make test` | Run tests for all components |
| `make clean` | Clean build artifacts and data |

## Common Workflows

### First Time Setup

```bash
# Install all dependencies
make setup
```

This will:
- Install Python dependencies for the model (pip)
- Install Python dependencies for the API (uv)
- Install Node.js dependencies for the UI (npm)

### Running All Services (Recommended)

```bash
# Single command to run everything
make run
```

This command:
1. Checks Docker is installed and running
2. Starts all services via Docker Compose:
   - LocalStack (S3 mock)
   - API server
   - UI server
   - Model service (placeholder)
3. Initializes S3 bucket
4. Displays service URLs
5. Tails logs (Ctrl+C to exit log view)

**Output:**
```
🚀 Starting Recycling Buddy - All Services

Starting services with Docker Compose...

⏳ Waiting for services to be ready...

Initializing LocalStack S3 bucket...

✅ All services started!

📍 Service URLs:
   API:          http://localhost:8000
   API Docs:     http://localhost:8000/docs
   UI:           http://localhost:5173
   LocalStack:   http://localhost:4566

📋 Useful commands:
   View logs:    make logs
   Stop all:     make stop

Tailing logs (Ctrl+C to exit)...
```

**Access:**
- API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- UI: http://localhost:5173
- LocalStack: http://localhost:4566

**To stop:**
Press `Ctrl+C` to exit logs, then:
```bash
make stop
```

### Running with Rebuild

```bash
make dev
```

Same as `make run`, but rebuilds Docker images first. Use this when:
- You've changed Dockerfile configurations
- You've added new dependencies
- Images need to be updated

This starts all services in Docker containers with hot reload enabled.

### Stopping Services

```bash
make stop
```

This will:
- Stop all Docker Compose services
- Kill any running uvicorn processes
- Clean up resources

### Viewing Logs

```bash
make logs
```

Shows live logs from all Docker Compose services. Press `Ctrl+C` to exit.

### Running Tests

```bash
make test
```

Runs tests for all components:
- Model tests (pytest)
- API tests (pytest via uv)
- UI tests (npm test)

### Cleaning Up

```bash
make clean
```

Removes:
- `__pycache__` directories
- `.pytest_cache` directories
- `node_modules` directories
- Build artifacts
- LocalStack data directory

## Advanced Usage

### Manual LocalStack Setup

If you need to set up LocalStack separately:

```bash
make init-localstack
```

This will:
- Start LocalStack container
- Wait for it to be ready
- Create the S3 bucket (`recycling-buddy-training`)
- Report success

The bucket creation is done with:
```bash
aws --endpoint-url=http://localhost:4566 s3 mb s3://recycling-buddy-training
```

### Docker Compose Detection

The Makefile automatically detects whether to use:
- `docker compose` (Docker Compose V2 plugin)
- `docker-compose` (standalone Docker Compose)

No configuration needed - it just works!

### Docker Health Check

The `make run` command includes a Docker health check that will:
- Verify Docker is installed
- Verify Docker daemon is running
- Exit with helpful error message if not

## Environment Variables

The API uses these environment variables (configured in `.env.dev`):

```env
S3_BUCKET=recycling-buddy-training
S3_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
```

These are automatically loaded when running via `make run`.

## Troubleshooting

### "Docker is not installed"

Install Docker Desktop from https://www.docker.com/products/docker-desktop

### "Docker daemon is not running"

Start Docker Desktop and wait for it to fully start.

### "LocalStack failed to start"

Check Docker has enough resources:
- Memory: At least 2GB recommended
- Disk: Ensure sufficient free space

View logs:
```bash
make logs
```

### Port conflicts

If ports 4566 or 8000 are in use:

**Find what's using the port:**
```bash
lsof -i :4566
lsof -i :8000
```

**Stop the conflicting service or change ports in docker-compose.yml**

### "make: command not found"

Install make:
- macOS: `xcode-select --install`
- Ubuntu/Debian: `sudo apt-get install build-essential`
- Windows: Use WSL2 or install via Chocolatey

## Integration with IDEs

### VS Code

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run API",
      "type": "shell",
      "command": "make run",
      "problemMatcher": [],
      "group": {
        "kind": "build",
        "isDefault": true
      }
    }
  ]
}
```

### IntelliJ/PyCharm

1. Go to Run → Edit Configurations
2. Add new "Shell Script" configuration
3. Set script path to: `/usr/bin/make`
4. Set script options to: `run`
5. Set working directory to project root

## Continuous Integration

The Makefile commands work well in CI/CD:

```yaml
# Example GitHub Actions
- name: Setup
  run: make setup

- name: Run tests
  run: make test

- name: Clean
  run: make clean
```

## File Structure

```
recycling-buddy/
├── Makefile                 # Main automation file (includes S3 setup)
├── docker-compose.yml       # Service definitions
├── scripts/
│   └── verify-upload.sh     # Upload verification
└── api/
    └── .env.dev             # Development environment variables
```

## Dependencies

### System Requirements

- **Make**: 3.81 or higher
- **Docker**: 20.10 or higher
- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **uv**: Latest version (installed via pip)

### Optional Tools

- `awscli-local`: Simplified LocalStack AWS CLI
  ```bash
  pip install awscli-local
  ```

## Contributing

When adding new make targets:

1. Add to `.PHONY` declaration
2. Add to help text
3. Document in this guide
4. Test on clean environment

Example:
```makefile
.PHONY: my-target

my-target:
	@echo "Doing something..."
	# Implementation
```

## Related Documentation

- [Upload Feature Documentation](./UPLOAD_FEATURE.md)
- [Quick Start Guide](./QUICKSTART_UPLOAD.md)
- [Scripts Documentation](./scripts/README.md)
- [API Documentation](./api/README.md)
