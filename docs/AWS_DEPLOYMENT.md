# AWS Deployment Guide

This is a deployment runbook, not a deployed stack or a security certification. AWS account, region, domain, lead processor, and private contact details have not been supplied, so no cloud resources or secrets have been created.

## Recommended topology

- Separate ECS Fargate services for the API and Next.js dashboard.
- Application Load Balancer with HTTPS listeners and certificates from ACM.
- Private subnets for tasks; security groups allow task ingress only from the ALB.
- Route 53 records for the dashboard and API hostnames.
- ECR repositories for versioned, scanned container images.
- Secrets Manager for `SANCTUM_API_KEY` and `SANCTUM_LEAD_WEBHOOK_TOKEN`.
- CloudWatch Logs, alarms, retention policies, and audit logging.
- S3 with versioning and lifecycle/retention policy for required backups and release artifacts.

## API task configuration

Build and push the root Dockerfile to ECR. The container listens on port 8000 and `/readyz` is healthy only when a valid API key is present. In the ECS task definition, configure `SANCTUM_API_KEY` using the `secrets` field referencing a Secrets Manager ARN. Do not place the value in task-definition plaintext or the container image.

Create a unique API key with at least 32 bytes of entropy, such as `secrets.token_urlsafe(48)`. Store it in Secrets Manager and grant the task execution role only the permissions required to read that secret. Restrict API routes at the ALB/network boundary; API key authentication does not replace TLS, authorization, tenant isolation, or rate limiting.

## Dashboard task configuration

Build `sanctum-dashboard/Dockerfile` with `NEXT_PUBLIC_SANCTUM_WS_URL` set to the intended public `wss://` API host. This variable is compiled into browser JavaScript and is public configuration; never put credentials in it.

At runtime, configure `SANCTUM_LEAD_WEBHOOK_URL` only after selecting and reviewing a processor. Configure `SANCTUM_LEAD_WEBHOOK_TOKEN` as an ECS task secret sourced from Secrets Manager. The lead form reports itself unavailable if the webhook URL is absent. Use an HTTPS endpoint; do not include credentials in its URL.

## Data protection and operations

- Select an AWS region and confirm residency, processor, and transfer requirements.
- Define CloudWatch retention and access restrictions; do not log submitted message bodies.
- Enable ECR image scanning and deploy immutable image digests.
- Back up only required application data; test restore and rollback procedures.
- Configure WAF or equivalent edge controls, rate limiting, abuse monitoring, TLS renewal, and alerting.
- Apply least-privilege IAM roles; do not reuse CI credentials in ECS tasks.
- Review the API's authorization and the behavior of each enabled scanner before exposing it.

## Before provisioning

Obtain the AWS account/region, domain/DNS authority, budget approval, webhook provider/endpoint, secret values entered directly in AWS, privacy-controller information, retention terms, support contact/SLA, and approved license agreement. Then provision infrastructure through a reviewed IaC plan. None of these actions is performed by this repository guide.
