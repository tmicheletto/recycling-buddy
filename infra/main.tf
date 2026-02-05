terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket       = "terraform-state-646385694251"
    key          = "recycling-buddy/terraform.tfstate"
    region       = "ap-southeast-2"
    encrypt      = true
    use_lockfile = false
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}
