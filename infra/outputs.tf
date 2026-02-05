output "api_url" {
  description = "App Runner API URL"
  value       = "https://${aws_apprunner_service.api.service_url}"
}

output "ui_url" {
  description = "S3 website URL"
  value       = "http://${aws_s3_bucket_website_configuration.ui.website_endpoint}"
}

output "ui_bucket" {
  description = "UI S3 bucket name for deployment"
  value       = aws_s3_bucket.ui.id
}

output "ecr_repository_url" {
  description = "ECR repository URL for pushing images"
  value       = aws_ecr_repository.api.repository_url
}

output "training_bucket" {
  description = "Training data S3 bucket name"
  value       = aws_s3_bucket.training.id
}

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = var.aws_region
}
