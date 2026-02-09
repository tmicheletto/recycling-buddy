# Example Terraform variables file
# Copy this to terraform.tfvars and fill in your values

# Project configuration
project_name = "recycling-buddy"
environment  = "dev"
aws_region   = "ap-southeast-2"

# ECS Fargate configuration
api_cpu           = 256
api_memory        = 512
api_desired_count = 1

# IAM Role ARNs (managed externally)
ecs_execution_role_arn = "arn:aws:iam::646385694251:role/recycling-buddy-ecs"
ecs_task_role_arn      = "arn:aws:iam::646385694251:role/recycling-buddy-api"
