output "api_url" {
  description = "ALB API URL"
  value       = "http://${aws_lb.api.dns_name}"
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

output "ecs_cluster_name" {
  description = "ECS cluster name for deployment"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name for deployment"
  value       = aws_ecs_service.api.name
}

output "data_bucket" {
  description = "Data S3 bucket name"
  value       = aws_s3_bucket.data.id
}

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = var.aws_region
}
