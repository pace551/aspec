variable "project" {
  description = "Project slug; becomes the Project tag on every resource"
  type        = string
  default     = "{{PROJECT}}"
}

variable "aws_region" {
  description = "Deployment region"
  type        = string
  default     = "us-east-1"
}
