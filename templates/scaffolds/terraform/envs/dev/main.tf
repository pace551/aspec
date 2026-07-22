# Root module for the dev environment (INF-TF-01): compose shared modules here.
# Environment differences are variable values, not divergent resources (INF-ENVS-06).

module "artifacts" {
  source = "../../modules/s3-private-bucket"

  bucket_name = "${var.project}-dev-artifacts"
}
