variable "project_name" {
  description = "Project identifier"
  type        = string
  default     = "recycling-buddy"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "ap-southeast-2"
}

variable "api_cpu" {
  description = "Fargate CPU units (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "api_memory" {
  description = "Fargate memory in MiB"
  type        = number
  default     = 512
}

variable "api_desired_count" {
  description = "Desired number of API tasks"
  type        = number
  default     = 1
}

variable "ecs_execution_role_arn" {
  description = "ARN of IAM role for ECS task execution (ECR pull + CloudWatch Logs, managed externally)"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ARN of IAM role for ECS task runtime (S3 access, managed externally)"
  type        = string
}
