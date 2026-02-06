# App Runner service
# Note: IAM roles are managed externally and provided via variables
resource "aws_apprunner_service" "api" {
  service_name = "${local.name_prefix}-api"

  source_configuration {
    image_repository {
      image_identifier      = "${aws_ecr_repository.api.repository_url}:latest"
      image_repository_type = "ECR"
      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          S3_BUCKET  = aws_s3_bucket.training.id
          AWS_REGION = var.aws_region
        }
      }
    }
    authentication_configuration {
      access_role_arn = var.apprunner_access_role_arn
    }
    auto_deployments_enabled = true
  }

  instance_configuration {
    cpu               = var.api_cpu
    memory            = var.api_memory
    instance_role_arn = var.apprunner_instance_role_arn
  }

  health_check_configuration {
    protocol = "HTTP"
    path     = "/health"
  }

  tags = {
    Name        = "${local.name_prefix}-api"
    Environment = var.environment
  }
}
