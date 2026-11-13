# Phase 1 live-ready wave

This first live-ready wave focuses on the operational control plane that is most realistic and most valuable for evidence-backed integration: GCP, ELK, Terraform, and Kafka.

## Objective

Move the following capability IDs into a real deployment pattern with explicit env vars, scoped authentication, health checks, and event publication:

- `security-capability:gcp-platform`
- `security-capability:observability`
- `security-capability:terraform-policy`
- `security-capability:kafka-event-bus`

## Module-by-module backlog

### 1) GCP platform adapter

- Capability ID: `security-capability:gcp-platform`
- Auth: service-account JSON or ADC in the target runtime
- Required env vars:
  - `SANCTUM_GCP_PROJECT_ID`
  - `SANCTUM_GCP_SERVICE_ACCOUNT_JSON` (optional if ADC is available)
  - `SANCTUM_GCP_SERVICE_ACCOUNT`
- Endpoint: `/api/v1/security-capabilities/security-capability:gcp-platform/evidence`
- Payload shape:
  ```json
  {
    "target": "edge-domain",
    "environment": "production",
    "capability_id": "security-capability:gcp-platform",
    "source_type": "gcp_api",
    "evidence": {
      "project_id": "prod-core-01",
      "service_accounts": ["svc-audit", "svc-terraform"],
      "resource_inventory": 154,
      "iam_model": "organization-level"
    },
    "status": "PLAN_ONLY"
  }
  ```
- Acceptance: health check must return `READY` only when the project ID and auth context are valid.

### 2) ELK observability adapter

- Capability ID: `security-capability:observability`
- Auth: API key or service account / Elasticsearch auth
- Required env vars:
  - `SANCTUM_ELK_ENDPOINT`
  - `SANCTUM_ELK_API_KEY`
  - `SANCTUM_ELK_INDEX_PATTERN`
- Endpoint: `/api/v1/security-capabilities/security-capability:observability/evidence`
- Payload shape:
  ```json
  {
    "target": "security-analytics",
    "environment": "production",
    "capability_id": "security-capability:elastic-observability",
    "source_type": "logging_api",
    "evidence": {
      "cluster_name": "prod-elk-cluster",
      "log_index": "security-*",
      "dashboard_rules": 42,
      "alerting_enabled": true
    },
    "status": "PLAN_ONLY"
  }
  ```
- Acceptance: live sync must fail closed when the endpoint or secret is absent.

### 3) Terraform policy adapter

- Capability ID: `security-capability:terraform-policy`
- Auth: Terraform CLI context, remote state, or signed workspace access
- Required env vars:
  - `SANCTUM_TERRAFORM_STATE_PATH`
  - `SANCTUM_TERRAFORM_WORKSPACE`
- Endpoint: `/api/v1/security-capabilities/security-capability:terraform-policy/evidence`
- Payload shape:
  ```json
  {
    "target": "platform-terraform",
    "environment": "production",
    "capability_id": "security-capability:terraform-policy",
    "source_type": "iac_api",
    "evidence": {
      "terraform_state": "prod-state.tfstate",
      "drift_report": "checked",
      "resource_count": 148,
      "workspace_name": "prod-core"
    },
    "status": "PLAN_ONLY"
  }
  ```
- Acceptance: the adapter exposes drift and state evidence only when real state or workspace access exists.

### 4) Kafka event bus adapter

- Capability ID: `security-capability:kafka-event-bus`
- Auth: SASL/SCRAM, mTLS, or secret-backed broker credentials
- Required env vars:
  - `SANCTUM_KAFKA_BOOTSTRAP_SERVERS`
  - `SANCTUM_KAFKA_TOPIC`
  - `SANCTUM_KAFKA_USERNAME` (if applicable)
  - `SANCTUM_KAFKA_PASSWORD` (if applicable)
- Endpoint: `/api/v1/security-capabilities/security-capability:kafka-event-bus/evidence`
- Payload shape:
  ```json
  {
    "target": "event-mesh",
    "environment": "production",
    "capability_id": "security-capability:kafka-event-bus",
    "source_type": "event_bus",
    "evidence": {
      "bootstrap_servers": ["broker-01:9092"],
      "topics": ["sanctum.evidence.normalized", "sanctum.alerts"],
      "event_bus_status": "configured"
    },
    "status": "PLAN_ONLY"
  }
  ```
- Acceptance: the producer/consumer bridge remains disabled unless the broker configuration is valid and accepted.

## Deployment order

1. GCP project and IAM validation
2. ELK endpoint validation and index access
3. Terraform state and drift validation
4. Kafka broker connectivity and topic publication
5. Common event schema publication and health validation

## Acceptance criteria

A capability enters live-ready only when all of the following are true:

- env vars are populated in the target environment
- auth is valid and scoped to least-privilege access
- endpoint connectivity is checked and recorded
- health check returns `READY` or `NOT_CONFIGURED`, never a false positive
- events are published using the common `sanctum-capability-event-v1` schema
- the adapter is registered and callable through the capability registry and API surface

## Implementation note

This repository already contains the adapter contracts and registry definitions for these modules. The remaining work is operational enablement: real deployment env vars, real auth material, and live validation to move each adapter from `NOT_CONFIGURED` to `READY`.
