terraform {
  required_version = ">= 1.5.0"

  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }
  }

  # Configure a remote backend per environment. Left commented so
  # `terraform init -backend=false` works out of the box for validation.
  # backend "s3" {
  #   bucket = "my-tf-state"
  #   key    = "chaos-engineering-lab/terraform.tfstate"
  #   region = "us-east-1"
  # }
}
