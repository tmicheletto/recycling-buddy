# infra/CLAUDE.md

Infrastructure component for Recycling Buddy monorepo.

## Purpose

Manages infrastructure, deployment, and operational concerns for the Recycling Buddy application including:
- Container orchestration and configuration
- Cloud infrastructure provisioning
- CI/CD pipelines
- Environment management
- Monitoring and logging

## Structure

```
infra/
├── docker/              # Docker configurations
│   ├── docker-compose.yml
│   └── Dockerfile.*     # Component-specific Dockerfiles
├── terraform/           # Infrastructure as Code (if using cloud)
├── k8s/                 # Kubernetes manifests (if applicable)
├── scripts/             # Deployment and operational scripts
└── README.md            # Infrastructure documentation
```

## Tech Stack

- **Containerization**: Docker, Docker Compose
- **Cloud Provider**: TBD (AWS/GCP/Azure)
- **CI/CD**: TBD (GitHub Actions/GitLab CI/CircleCI)
- **Infrastructure as Code**: TBD (Terraform/CloudFormation/Pulumi)

## Development Principles

1. **Environment Parity**: Dev, staging, and prod should be as similar as possible
2. **Infrastructure as Code**: All infrastructure should be version-controlled
3. **Secrets Management**: Never commit secrets; use environment variables or secret managers
4. **Reproducibility**: Anyone should be able to spin up the stack with one command
5. **Documentation**: Keep deployment and operational procedures documented

## Docker Configurations

### Local Development

- `docker-compose.yml` orchestrates all services (API, UI, model)
- Each component has its own Dockerfile
- Use volumes for hot-reloading during development
- Services communicate via Docker network

## Development Workflow

- Always run `terraform validate` and `terraform fmt` before committing.

### Production Builds

- Multi-stage builds to minimize image size
- Health checks defined for each service
- Resource limits and restart policies configured

## Environment Management

- The AWS_REGION is always **ap-southeast-2**

### Environment Variables

Manage environment-specific configurations:

- **Development**: `.env` files (gitignored)
- **Staging/Production**: Cloud-managed secrets or secret manager

### Configuration Files

- Keep environment configs in `infra/environments/`
- Use templates for configuration with placeholders
- Document all required environment variables

## Deployment

### Local Development

```bash
# From project root
docker-compose up --build

# Or using Make
make dev
```

### Cloud Deployment

TBD based on chosen cloud provider:
- Deployment scripts in `infra/scripts/`
- IaC configurations in `infra/terraform/` or equivalent
- CI/CD pipeline definitions in `.github/workflows/` or equivalent

## CI/CD Pipeline

### Pipeline Stages

1. **Build**: Build Docker images for each component
2. **Test**: Run unit and integration tests
3. **Lint**: Code quality checks
4. **Security**: Vulnerability scanning
5. **Deploy**: Deploy to target environment (staging/prod)

### Deployment Strategy

- **Staging**: Auto-deploy on merge to `main`
- **Production**: Manual approval or tagged releases
- **Rollback**: Keep previous versions available for quick rollback

## Monitoring and Logging

### Logging Strategy

- Centralized logging for all services
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Monitoring

TBD based on requirements:
- Application metrics (request rates, error rates, latency)
- Infrastructure metrics (CPU, memory, disk, network)
- Alerting on critical errors and performance degradation

## Common Tasks

### Adding a New Service

1. Create Dockerfile in `infra/docker/`
2. Add service definition to `docker-compose.yml`
3. Configure networking and dependencies
4. Add health check endpoint
5. Update documentation

### Updating Infrastructure

1. Make changes to IaC files (Terraform/CloudFormation)
2. Run plan/preview to validate changes
3. Apply changes in staging first
4. Test thoroughly before production deployment

### Troubleshooting Deployment Issues

1. Check service logs: `docker-compose logs [service-name]`
2. Verify environment variables are set correctly
3. Check network connectivity between services
4. Verify resource availability (memory, disk space)
5. Review recent infrastructure changes

## Security Considerations

1. **Secrets**: Use secret management tools, never commit to git
2. **Network**: Minimize exposed ports, use internal networks
3. **Images**: Scan for vulnerabilities, use official base images
4. **Access**: Implement least-privilege access controls
5. **Updates**: Keep dependencies and base images updated

## Backup and Disaster Recovery

- Database backup strategy (if applicable)
- Regular backups of critical data
- Documented recovery procedures
- Test recovery process periodically

## Cost Optimization

- Right-size resources based on actual usage
- Use auto-scaling where appropriate
- Monitor and alert on cost anomalies
- Regular review of resource utilization

## Documentation Requirements

When making infrastructure changes:

1. Update this CLAUDE.md if architectural changes
2. Update README.md with operational procedures
3. Document environment variables in `.env.example`
4. Keep runbooks for common operational tasks
5. Update disaster recovery procedures if affected
