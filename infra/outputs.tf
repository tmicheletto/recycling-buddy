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

output "apprunner_service_arn" {
  description = "App Runner service ARN for deployment updates"
  value       = aws_apprunner_service.api.arn
}

output "apprunner_service_name" {
  description = "App Runner service name for deployment"
  value       = aws_apprunner_service.api.service_name
}

output "apprunner_access_role_arn" {
  description = "IAM role ARN for App Runner to access ECR"
  value       = var.apprunner_access_role_arn
}

output "data_bucket" {
  description = "Data S3 bucket name"
  value       = aws_s3_bucket.data.id
}

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = var.aws_region
}
