# Example single-table definition (STK-DDB). Rename, prune unused GSIs, and keep it
# in lockstep with docs/access-patterns.md — every index here answers a pattern row.
resource "aws_dynamodb_table" "app" {
  name         = "{project}-main"
  billing_mode = "PAY_PER_REQUEST" # on-demand until usage proves otherwise (STK-DDB-02)
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }
  attribute {
    name = "GSI1PK"
    type = "S"
  }
  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at" # epoch seconds (STK-DDB-05)
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true # OPS-BACKUP
  }
}
