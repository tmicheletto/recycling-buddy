# Recycling Buddy Infrastructure

Terraform configuration for deploying Recycling Buddy to AWS using App Runner and S3.

## Architecture

- **API**: AWS App Runner (FastAPI container)
- **UI**: S3 Static Website (React SPA)
- **Training Data**: S3 Bucket (private)
- **Container Registry**: Amazon ECR

## Prerequisites

1. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```

2. **Terraform** >= 1.0
   ```bash
   brew install terraform  # macOS
   # or download from https://www.terraform.io/downloads
   ```

3. **Docker** for building API images
   ```bash
   # Verify Docker is running
   docker --version
   ```

## Setup

### 1. Initialize Terraform

```bash
cd infra
terraform init
```

### 2. Review Configuration

```bash
# Check what will be created
terraform plan

# Should show approximately 10 resources:
# - 2 S3 buckets + configurations
# - 1 ECR repository + lifecycle policy
# - 2 IAM roles + policies
# - 1 App Runner service
```

### 3. Create Infrastructure

```bash
terraform apply
# Review the plan and type 'yes' to confirm
```

This will create all AWS resources. Save the outputs:
- `api_url`: Your API endpoint
- `ui_url`: Your UI website
- `ecr_repository_url`: Where to push Docker images
- `training_bucket`: S3 bucket for training data

## Deployment Workflow

### Deploy API

```bash
# 1. Get ECR login credentials
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $(terraform output -raw ecr_repository_url)

# 2. Build API Docker image
cd ../api
docker build -t recycling-buddy-api .

# 3. Tag and push to ECR
docker tag recycling-buddy-api:latest $(cd ../infra && terraform output -raw ecr_repository_url):latest
docker push $(cd ../infra && terraform output -raw ecr_repository_url):latest

# App Runner will automatically deploy the new image (auto-deploy enabled)
```

### Deploy UI

```bash
# 1. Build UI with API URL
cd ../ui
VITE_API_URL=$(cd ../infra && terraform output -raw api_url) npm run build

# 2. Sync to S3
aws s3 sync dist/ s3://$(cd ../infra && terraform output -raw ui_bucket)/ --delete

# Your UI is now live at the ui_url from terraform outputs
```

## Configuration

### Variables

You can customize deployment by creating a `terraform.tfvars` file:

```hcl
project_name = "recycling-buddy"
environment  = "prod"
aws_region   = "us-west-2"
api_cpu      = "0.5 vCPU"
api_memory   = "1 GB"
```

### Environment Variables

The API receives these environment variables automatically:
- `S3_BUCKET`: Training data bucket name
- `AWS_REGION`: AWS region

The App Runner instance role has permissions to read/write the training bucket.

## Updating Infrastructure

```bash
# After modifying .tf files
terraform plan   # Review changes
terraform apply  # Apply changes
```

## Accessing Your Application

```bash
# Get all URLs
terraform output

# Open UI in browser
open $(terraform output -raw ui_url)

# Test API health
curl $(terraform output -raw api_url)/health
```

## Monitoring

### App Runner Logs

```bash
# View logs in AWS Console
aws apprunner list-services
aws apprunner describe-service --service-arn <service-arn>
```

Or use the AWS Console:
1. Go to AWS App Runner
2. Select your service
3. View "Logs" tab

### S3 Access Logs

Enable S3 access logging if needed:
```bash
aws s3api put-bucket-logging --bucket <ui-bucket> --bucket-logging-status ...
```

## Cost Estimate

| Resource | Monthly Cost (us-east-1) |
|----------|-------------------------|
| App Runner (0.25 vCPU, 0.5GB) | ~$5-15 (pay per use) |
| S3 Storage (minimal) | < $1 |
| ECR Storage | < $1 |
| **Total** | **~$7-17/month** |

App Runner charges:
- $0.064/vCPU-hour provisioned
- $0.007/GB-hour provisioned
- Plus request/data transfer costs

## Cleanup

To destroy all resources and stop charges:

```bash
# WARNING: This will delete all data in S3 buckets
terraform destroy
```

Note: You may need to empty S3 buckets manually if they contain objects.

## Troubleshooting

### App Runner Deployment Failed

1. Check ECR image exists:
   ```bash
   aws ecr describe-images --repository-name $(terraform output -raw ecr_repository_url | cut -d'/' -f2)
   ```

2. View App Runner logs in AWS Console

3. Verify IAM roles have correct permissions

### S3 Website Not Loading

1. Check bucket policy is applied:
   ```bash
   aws s3api get-bucket-policy --bucket $(terraform output -raw ui_bucket)
   ```

2. Verify files were uploaded:
   ```bash
   aws s3 ls s3://$(terraform output -raw ui_bucket)/
   ```

3. Check public access settings are correct

### CORS Issues

If UI can't reach API, add CORS configuration to FastAPI:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Security Notes

- **S3 UI Bucket**: Publicly readable (required for static website)
- **S3 Training Bucket**: Private, only accessible by App Runner
- **App Runner**: Public endpoint, add authentication if needed
- **ECR**: Private, only accessible by App Runner via IAM role

## Future Enhancements

- Add CloudFront CDN for HTTPS on UI
- Configure custom domain with Route 53
- Add CI/CD with GitHub Actions
- Store Terraform state in S3 backend
- Add CloudWatch alarms and dashboards
- Implement API authentication (Cognito/Auth0)
