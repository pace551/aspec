# Root module for the prod environment (INF-TF-01). Same shape as envs/dev —
# prod is dev-shaped with prod values (INF-ENVS-06). Applied via CI at T4 (INF-TF-05).

module "artifacts" {
  source = "../../modules/s3-private-bucket"

  bucket_name = "${var.project}-prod-artifacts"
}
