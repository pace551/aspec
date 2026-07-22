output "bucket_id" {
  description = "Bucket name"
  value       = aws_s3_bucket.this.id
}

output "bucket_arn" {
  description = "Bucket ARN, for IAM policy statements (SEC-AUTHZ least privilege)"
  value       = aws_s3_bucket.this.arn
}
