# App Runner service
# Note: IAM roles are managed externally and provided via variables
#
# IMPORTANT: The App Runner service depends on an image existing in ECR.
# Push an image to ECR before the first `terraform apply`, or use the
# `var.deploy_apprunner` flag to skip this resource until an image is ready.
resource "aws_apprunner_service" "api" {
  count        = var.deploy_apprunner ? 1 : 0
  service_name = "${local.name_prefix}-api"

  source_configuration {
    image_repository {
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
    # Let App Runner auto-deploy when new images are pushed to ECR.
    # This means Terraform won't see drift from image updates.
    auto_deployments_enabled = true
  }

  instance_configuration {
    cpu               = var.api_cpu
    memory            = var.api_memory
    instance_role_arn = var.apprunner_instance_role_arn
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  tags = {
    Name = "${local.name_prefix}-api"
  }

  depends_on = [aws_ecr_lifecycle_policy.api]
}
