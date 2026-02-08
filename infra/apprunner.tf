# App Runner service
# Note: IAM roles are managed externally and provided via variables
# Note: Initial deployment and image updates are managed by CI/CD pipeline
resource "aws_apprunner_service" "api" {
  service_name = "${local.name_prefix}-api"

  source_configuration {
    image_repository {
      # Point to our private ECR repository with :latest tag
      # CI/CD pipeline will update this with specific commit SHAs
      image_identifier      = "${aws_ecr_repository.api.repository_url}:latest"
      image_repository_type = "ECR"
      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          S3_BUCKET  = aws_s3_bucket.data.id
          AWS_REGION = var.aws_region
        }
      }
    }
    authentication_configuration {
      access_role_arn = var.apprunner_access_role_arn
    }
    # Disable auto-deployments - CI/CD pipeline manages deployments explicitly
    auto_deployments_enabled = false
  }

  instance_configuration {
    cpu               = var.api_cpu
    memory            = var.api_memory
    instance_role_arn = var.apprunner_instance_role_arn
  }

  health_check_configuration {
    protocol = "HTTP"
    path     = "/"
  }

  tags = {
    Name = "${local.name_prefix}-api"
  }

  # Prevent Terraform from reverting image updates made by CI/CD
  lifecycle {
    ignore_changes = [
      source_configuration[0].image_repository[0].image_identifier,
      source_configuration[0].image_repository[0].image_repository_type
    ]
  }
}
