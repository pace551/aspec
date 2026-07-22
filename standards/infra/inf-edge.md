---
id: INF-EDGE
title: Networking & Edge
family: INF
version: 1.0.0
status: active
tiers:
  T1: advisory
  T2: advisory
  T3: required
  T4: required
stacks: [aws, web]
triggers:
  - dns
  - route53
  - domain
  - tls
  - certificate
  - https
  - cloudfront
  - cdn
  - waf
  - security group
  - vpc
  - nat gateway
  - load balancer
  - public bucket
requires: []
verification:
  - cmd: "sh -c '! git grep -qE \"acl[[:space:]]*=[[:space:]]*\\\"public-read\" -- \"*.tf\"'"
    expect: "exit 0 — no public-read bucket ACLs in tracked .tf"
    layer: G
    rules: [INF-EDGE-05]
  - cmd: "sh -c '! git grep -qE \"from_port[[:space:]]*=[[:space:]]*22([^0-9]|$)\" -- \"*.tf\"'"
    expect: "exit 0 — no security-group rule opens port 22 (SSM Session Manager replaces SSH)"
    layer: G
    rules: [INF-EDGE-06]
  - cmd: "sh -c '! git grep -q \"aws_nat_gateway\" -- \"*.tf\"'"
    expect: "exit 0 — no NAT gateway; presence requires James's recorded consent (waiver)"
    layer: G
    rules: [INF-EDGE-07]
  - cmd: "attest: public dns records live in a route53 hosted zone managed by tofu"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-EDGE-01]
    tiers: [T3, T4]
  - cmd: "attest: all tls certs are acm-issued with dns validation and auto-renewal — none hand-managed"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-EDGE-02]
    tiers: [T3, T4]
  - cmd: "attest: public web surfaces sit behind cloudfront (caching, tls termination, waf attachment point)"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-EDGE-03]
    tiers: [T3, T4]
  - cmd: "attest: waf with the aws managed core rule set is attached to public entry points"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-EDGE-04]
    tiers: [T4]
  - cmd: "attest: any s3 content served publicly goes through cloudfront oac; every bucket keeps block-public-access on"
    expect: "explicit yes in GOVERNANCE.md attestations"
    layer: A
    rules: [INF-EDGE-05]
last_review: 2026-07-22
---

# Networking & Edge (INF-EDGE)

## Abstract

How traffic reaches the things James deploys: Route53 for DNS, ACM for certificates
that renew themselves, CloudFront in front of anything public (with WAF attached at
T4), S3 that is never public directly, security groups that admit only 443/80 at the
edge, and SSH replaced by SSM Session Manager. The standing bias is
serverless/managed over VPC-heavy designs — the NAT gateway is the canonical hidden
cost and its presence requires recorded consent. The greppable prohibitions
(public-read ACLs, open port 22, NAT gateways) bind wherever `.tf` exists; the
edge-architecture rules harden at T3+ where there is a public surface at all.

## Normative Rules

### INF-EDGE-01 — Public DNS MUST live in Route53, managed by tofu

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

One hosted zone per domain, records as `aws_route53_record` resources — never
hand-edited in the console (INF-TF drift rule) and never scattered across registrar
panels. Registration can stay at an external registrar; delegation points at the
zone's name servers. Alias records (free, apex-capable) over CNAMEs for AWS targets.

### INF-EDGE-02 — TLS everywhere via ACM with DNS validation; certificates are never hand-managed

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

Every public endpoint serves HTTPS with an ACM certificate (free) using DNS validation,
so renewal is automatic and unattended — the failure mode being retired is the
manually-renewed cert that expires on a weekend. No Let's Encrypt certbot cron on a
host, no purchased certs, no private keys on disk (an ACM key is unexportable — that
is a feature). CloudFront/ACM-for-CloudFront certs live in us-east-1; plan for it.
HTTP exists only as a 301 to HTTPS (SEC-WEB carries HSTS and header details).

### INF-EDGE-03 — Public T3+ web surfaces MUST sit behind CloudFront

**Tiers**: T1–T2 advisory · T3–T4 required — **Layer**: A (attestation)

CloudFront is the single front door: caching (origin does less work — FinOps), TLS
termination, HTTP/2+3, and the attachment point for WAF (-04) and OAC (-05). Static
sites are S3+OAC+CloudFront; APIs gain origin shielding and a place to rate-limit
before compute bills. Skipping it is acceptable only for non-browser API-only services
already throttled at API Gateway (INF-SERVERLESS-10) — record the reason.

### INF-EDGE-04 — WAF with the AWS managed core rule set MUST be attached at T4

**Tiers**: T1–T3 advisory · T4 required — **Layer**: A (attestation)

At T4 (money/PII), `AWSManagedRulesCommonRuleSet` + `KnownBadInputs` on the CloudFront
distribution or public ALB, plus a rate-based rule as backstop. Cost honesty for T3:
WAF's ~$5-10/month floor is real money at hobby scale — at T3 prefer API Gateway
throttling and application-level limits first, and step up when exposure or traffic
justifies it (C6: the upgrade is a conscious spend decision, not a default).

### INF-EDGE-05 — S3 buckets are private by default; public content ONLY via CloudFront OAC

**Tiers**: all required — **Layer**: G (acl grep) + A (attestation)

Every bucket keeps all four block-public-access flags on (scaffold module does this).
"Public" S3 content means: private bucket + CloudFront Origin Access Control + a bucket
policy admitting only that distribution. Public-read ACLs and `block_public_policy =
false` are the S3-leak incident class that keeps making the news — the G check greps
`acl = "public-read"` out of existence at every tier.

### INF-EDGE-06 — Security groups MUST be least-privilege; no open SSH — use SSM Session Manager

**Tiers**: all required — **Layer**: G (port-22 grep) + A

Ingress `0.0.0.0/0` is legitimate only for 443 (and 80-redirect) on the public edge
(CloudFront/ALB/API Gateway). Everything behind it admits only its upstream security
group by reference, never CIDR ranges. Port 22 stays closed everywhere: shell access
on the rare EC2 box goes through SSM Session Manager (IAM-authed, MFA-able, logged —
no keypair files, no open port). Egress SHOULD also be scoped on T4 services holding
sensitive data.

### INF-EDGE-07 — Prefer serverless/managed designs; a NAT gateway requires James's recorded consent

**Tiers**: all required — **Layer**: G

At solo scale, default to services with no VPC to run: Lambda, Fargate in public
subnets with SG-only ingress, DynamoDB, S3. The moment private subnets appear, the NAT
gateway follows at ~$32/month + data processing before any value ships — the canonical
hidden AWS cost (OPS-FINOPS, C6). The G check fails on `aws_nat_gateway`, forcing a
consent-bearing waiver. Cheaper first moves: public subnets + strict SGs, VPC
endpoints for S3/DynamoDB (gateway endpoints are free), or questioning why the VPC
exists at all.

## Verification

| # | Command | Passes when | Backs rules |
|---|---|---|---|
| 1 | `! git grep -qE 'acl\s*=\s*"public-read' -- "*.tf"` | no public-read ACLs | INF-EDGE-05 |
| 2 | `! git grep -qE 'from_port\s*=\s*22([^0-9]|$)' -- "*.tf"` | no SG opens port 22 | INF-EDGE-06 |
| 3 | `! git grep -q aws_nat_gateway -- "*.tf"` | no NAT gateway (presence ⇒ consent waiver) | INF-EDGE-07 |
| 4-8 | attestation checklist (one per rule; -01/-02/-03 at T3+, -04 at T4) | explicit yes recorded | INF-EDGE-01…05 |

**Remediation:** public-read ACL → block-public-access on, serve via CloudFront OAC
(worked example) · port 22 rule → delete it, use `aws ssm start-session
--target i-…` · NAT gateway hit → try gateway VPC endpoints / public-subnet+SG design;
if genuinely needed, record consent + monthly cost as a waiver · cert expiring
manually → reissue in ACM with DNS validation, delete the manual renewal calendar
entry.

## Worked Example

Static-site edge, the full INF-EDGE shape in one fragment (bucket module from
`templates/scaffolds/terraform/` stays fully private):

```hcl
resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "${var.project}-site-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "site" {
  enabled = true
  origin {
    domain_name              = module.site_bucket.bucket_regional_domain_name
    origin_id                = "s3-site"
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }
  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate.site.arn # us-east-1, DNS-validated
    ssl_support_method  = "sni-only"
  }
  # web_acl_id = aws_wafv2_web_acl.core.arn   # attach at T4 (INF-EDGE-04)
  default_cache_behavior {
    viewer_protocol_policy = "redirect-to-https"
    target_origin_id       = "s3-site"
    cache_policy_id        = data.aws_cloudfront_cache_policy.optimized.id
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
  }
  restrictions { geo_restriction { restriction_type = "none" } }
}

# Bucket policy: only this distribution may read — the bucket itself stays blocked.
data "aws_iam_policy_document" "site_read" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${module.site_bucket.bucket_arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.site.arn]
    }
  }
}
```

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `acl = "public-read"` to "just serve the files" | The S3 leak incident class, verbatim | Private bucket + CloudFront OAC (-05) |
| certbot cron on an EC2 box | Renewal breaks silently; key material on disk | ACM + DNS validation (-02) |
| Port 22 open "just to my IP" | IPs rotate; the rule outlives the laptop | SSM Session Manager (-06) |
| `0.0.0.0/0` ingress on an app SG | Bypasses the edge; every port a probe target | SG-references from the LB only (-06) |
| Private subnets + NAT by template habit | ~$32/mo + data fees before any traffic | Public subnet + strict SG, or VPC endpoints (-07) |
| DNS records hand-edited in the console | Drift; unrebuildable from code | `aws_route53_record` in tofu (-01) |
| WAF everywhere at T1-T3 "for security" | Pays an enterprise premium at hobby scale | Throttling first; WAF at T4 (-04) |
| CloudFront skipped, ALB serves users directly | No cache, no WAF point, origin pays full load | CloudFront front door (-03) |

## References

- AWS S3 Block Public Access + CloudFront OAC docs — the mechanism pair behind -05.
- AWS ACM user guide (DNS validation, managed renewal) — why -02 bans hand-managed certs.
- AWS SSM Session Manager docs — the port-22 replacement in -06.
- AWS VPC pricing (NAT gateway hourly + per-GB) — the ~$32/month floor cited in -07.
- AWS WAF managed rule groups + pricing — scope and the T3 cost note in -04.

## Changelog

- **1.0.0** (2026-07-22) — Initial version.
