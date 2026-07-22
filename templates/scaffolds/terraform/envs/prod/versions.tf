# Pinned core + providers (INF-TF-08). `tofu init` writes .terraform.lock.hcl — commit it.
terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # Mandatory tag set on every resource (INF-TF-06) — feeds OPS-FINOPS cost allocation.
  default_tags {
    tags = {
      Project   = var.project
      Env       = "prod"
      ManagedBy = "tofu"
    }
  }
}
