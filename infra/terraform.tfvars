# Example Terraform variables file
# Copy this to terraform.tfvars and fill in your values

# Project configuration
project_name = "recycling-buddy"
environment  = "dev"
aws_region   = "ap-southeast-2"

# App Runner configuration
api_cpu    = "0.25 vCPU"
api_memory = "0.5 GB"

# IAM Role ARNs (managed externally)
# These roles must be created outside of this Terraform configuration

# Role for App Runner to access ECR during build/deployment
# Required permissions: AWSAppRunnerServicePolicyForECRAccess
apprunner_access_role_arn = "arn:aws:iam::646385694251:role/recycling-buddy-api-role"

# Role for App Runner instance at runtime
# Required permissions: S3 access to training bucket
apprunner_instance_role_arn = "arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME"
