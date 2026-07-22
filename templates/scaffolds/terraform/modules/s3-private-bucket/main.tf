# Example shared module: a private, versioned, encrypted S3 bucket.
# Demonstrates the house module conventions:
#   - private-by-default (INF-EDGE-05: public content only ever via CloudFront OAC)
#   - prevent_destroy on stateful resources (INF-TF-09)
#   - no tags block — Project/Env/ManagedBy arrive via the root's default_tags (INF-TF-06)

resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name

  lifecycle {
    # Stateful resource: a destroy must be a deliberate two-step (INF-TF-09).
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      # SSE-S3: free. Switch to aws:kms only when a compliance need pays for it (C6).
      sse_algorithm = "AES256"
    }
  }
}
