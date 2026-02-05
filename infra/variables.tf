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
  description = "App Runner CPU allocation"
  type        = string
  default     = "0.25 vCPU"
}

variable "api_memory" {
  description = "App Runner memory allocation"
  type        = string
  default     = "0.5 GB"
}
