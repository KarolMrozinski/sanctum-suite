# Production Runbook: GCP + ELK + Terraform + Kafka (Phase 1 live-ready)

## Scope
This runbook defines the operational checklist for the first live-ready integration wave in SANCTUM-SUITE. The target integration set is:
- GCP: cloud inventory, IAM policy, logs, monitoring, and project metadata
- ELK: telemetry search, evidence indexing, and observability correlation
- Terraform: remote state, workspace metadata, drift, and execution evidence
- Kafka: normalized event transport for capability snapshots and evidence events

Important: a capability remains in `NOT_CONFIGURED` until all mandatory environment variables, auth material, endpoint reachability, RBAC, and health checks are validated in the target environment. It is promoted to `READY` only after live evidence is observed and policy validation passes.

## 1. Preconditions
- [ ] An operator-managed secret store is in use for all tokens, passwords, certs, and service-account JSON.
- [ ] The deployment is isolated to the production namespace / environment and is not running in a shared dev context.
- [ ] `SANCTUM_AUTHORIZED_TARGETS` contains only explicit, approved hosts/ports.
- [ ] TLS is enforced for all external service connections; private CA bundles are mounted as read-only files.
- [ ] Service accounts and users are restricted to least-privilege access.
- [ ] A network allowlist is approved for GCP, ELK, Terraform SaaS, and Kafka brokers.
- [ ] The operator has reviewed and approved the targeted evidence schema and retention window.

## 2. Required env vars
Populate these in the deployment secret manager or Kubernetes Secret; never commit them to source control.

### GCP
- [ ] `SANCTUM_GCP_PROJECT_ID`
- [ ] `SANCTUM_GCP_REGION`
- [ ] `SANCTUM_GCP_SERVICE_ACCOUNT`
- [ ] `SANCTUM_GCP_SERVICE_ACCOUNT_JSON`
- [ ] `SANCTUM_GCP_API_SCOPE`
- [ ] `SANCTUM_GCP_KMS_KEYRING`
- [ ] `SANCTUM_GCP_KMS_KEY`

### ELK
- [ ] `SANCTUM_ELK_ENDPOINT`
- [ ] `SANCTUM_ELK_API_KEY` or `SANCTUM_ELK_USERNAME` + `SANCTUM_ELK_PASSWORD`
- [ ] `SANCTUM_ELK_INDEX_PATTERN`
- [ ] `SANCTUM_ELK_CA_CERT`
- [ ] `SANCTUM_ELK_TLS_VERIFY=true`

### Terraform
- [ ] `SANCTUM_TERRAFORM_API_URL`
- [ ] `SANCTUM_TERRAFORM_ORG`
- [ ] `SANCTUM_TERRAFORM_WORKSPACE`
- [ ] `SANCTUM_TERRAFORM_TOKEN`
- [ ] `SANCTUM_TERRAFORM_STATE_PATH`
- [ ] `SANCTUM_TERRAFORM_CA_CERT`

### Kafka
- [ ] `SANCTUM_KAFKA_BOOTSTRAP_SERVERS`
- [ ] `SANCTUM_KAFKA_TOPIC`
- [ ] `SANCTUM_KAFKA_USERNAME`
- [ ] `SANCTUM_KAFKA_PASSWORD`
- [ ] `SANCTUM_KAFKA_SECURITY_PROTOCOL`
- [ ] `SANCTUM_KAFKA_SASL_MECHANISM`
- [ ] `SANCTUM_KAFKA_SSL_CA_LOCATION`

### Common
- [ ] `SANCTUM_AUTHORIZED_TARGETS`
- [ ] `SANCTUM_ENVIRONMENT=prod`
- [ ] `SANCTUM_API_KEY` or equivalent service gateway identity

## 3. RBAC and authorization matrix

### GCP
- [ ] Service account has `roles/resourcemanager.viewer`
- [ ] Service account has `roles/iam.securityReviewer`
- [ ] Service account has `roles/logging.viewer`
- [ ] Service account has `roles/monitoring.viewer`
- [ ] Service account has `roles/compute.viewer`
- [ ] KMS access is granted only for the required signing/encryption path
- [ ] No broad `roles/editor` or organization-admin grants are used
- [ ] Project-level IAM is validated with a non-production test project before prod activation

### ELK
- [ ] API key or user is restricted to `sanctum-*` indices only
- [ ] Cluster privileges are limited to `monitor`, `read`, and required write/index actions
- [ ] Kibana admin or superuser rights are not assigned to the automation identity
- [ ] Search is limited to the allowlisted index pattern
- [ ] TLS certificate validation is enabled

### Terraform
- [ ] API token has read access only to the targeted org/workspace unless explicit write mode is approved
- [ ] Writes are denied unless a dedicated automation identity is intentionally created
- [ ] Workspace metadata access is verified before live polling begins
- [ ] No cross-org access is allowed

### Kafka
- [ ] Producer ACL grants write to `sanctum.events` only
- [ ] Consumer ACL grants read to `sanctum.events` only
- [ ] Broker SASL/SCRAM or mTLS is enforced and validated
- [ ] Admin ACLs are scoped to the minimum required control topic(s)
- [ ] TLS CA trust is pinned to the approved cluster CA

## 4. Network, TLS, and certificate prerequisites
- [ ] GCP endpoint allowlist includes `cloudresourcemanager.googleapis.com:443`, `logging.googleapis.com:443`, `monitoring.googleapis.com:443`, and any required IAM endpoints.
- [ ] ELK endpoint allowlist includes the exact cluster host and port, e.g. `elk.internal.example:9200`.
- [ ] Terraform SaaS endpoint allowlist includes `app.terraform.io:443` or private Terraform Enterprise host.
- [ ] Kafka brokers are explicitly listed in `SANCTUM_KAFKA_BOOTSTRAP_SERVERS` and reachable over TLS/SASL.
- [ ] Private CA certificates are mounted read-only in the workload and not embedded into source code.
- [ ] Hostname verification is enabled for the TLS client; certificate SANs match internal identity names.

## 5. Implementation sequence
### Step 1: GCP
- [ ] Validate service account JSON parses and has a valid `client_email`
- [ ] Confirm project exists and is reachable
- [ ] Confirm `projects.list` or equivalent call works with the granted permissions
- [ ] Confirm IAM and Cloud Logging metadata are readable
- [ ] Confirm the service account can fetch key audit metadata from the target project
- [ ] Confirm a representative project inventory is returned

### Step 2: ELK
- [ ] Verify `GET ${SANCTUM_ELK_ENDPOINT}/_cluster/health` returns `green` or `yellow` with expected role access
- [ ] Verify `GET ${SANCTUM_ELK_ENDPOINT}/_cat/indices` lists existing indices
- [ ] Verify a test document can be written to a temporary index using the configured index pattern
- [ ] Verify `POST ${SANCTUM_ELK_ENDPOINT}/_search` returns valid JSON with expected fields
- [ ] Verify permission to read only `sanctum-*` indices is active

### Step 3: Terraform
- [ ] Confirm the Terraform API endpoint is reachable with the workspace token
- [ ] Confirm the target org/workspace exists and is active
- [ ] Confirm runs and state metadata are readable
- [ ] Confirm latest run status can be retrieved without cross-workspace access
- [ ] Confirm the state path is mounted and readable in the host or container if local state is required

### Step 4: Kafka
- [ ] Verify all Kafka brokers in `SANCTUM_KAFKA_BOOTSTRAP_SERVERS` resolve and are reachable
- [ ] Verify topic `SANCTUM_KAFKA_TOPIC` exists
- [ ] Verify producer can send a test message with the configured credentials
- [ ] Verify consumer can read the message back and confirm offset progression
- [ ] Verify ACLs reject unauthorized or unrelated topics

### Step 5: End-to-end event flow
- [ ] A capability snapshot is generated using the normalized event schema
- [ ] The event is published to Kafka on `SANCTUM_KAFKA_TOPIC`
- [ ] Kafka consumer receives the payload and confirms the `event_id`
- [ ] The payload is indexable in ELK under the configured index pattern
- [ ] A GCP/terraform source emits evidence without manual intervention
- [ ] The resulting evidence is visible in the Sanctum API status endpoints

## 6. Required validation commands
Run these commands in the target runtime environment before promoting to `READY`.

### GCP
```bash
gcloud auth activate-service-account --key-file=/path/to/service-account.json
gcloud config set project "$SANCTUM_GCP_PROJECT_ID"
gcloud projects describe "$SANCTUM_GCP_PROJECT_ID"
gcloud asset search-all-resources --scope=project --project="$SANCTUM_GCP_PROJECT_ID"
```

### ELK
```bash
curl -sS --cert /path/to/client.crt --key /path/to/client.key --cacert "$SANCTUM_ELK_CA_CERT" \
  -u "$SANCTUM_ELK_USERNAME:$SANCTUM_ELK_PASSWORD" \
  "$SANCTUM_ELK_ENDPOINT/_cluster/health"

curl -sS --cert /path/to/client.crt --key /path/to/client.key --cacert "$SANCTUM_ELK_CA_CERT" \
  -u "$SANCTUM_ELK_USERNAME:$SANCTUM_ELK_PASSWORD" \
  "$SANCTUM_ELK_ENDPOINT/_cat/indices?v"
```

### Terraform
```bash
curl -sS -H "Authorization: Bearer $SANCTUM_TERRAFORM_TOKEN" \
  "$SANCTUM_TERRAFORM_API_URL/organizations/$SANCTUM_TERRAFORM_ORG/workspaces"

curl -sS -H "Authorization: Bearer $SANCTUM_TERRAFORM_TOKEN" \
  "$SANCTUM_TERRAFORM_API_URL/workspaces/$(workspace_id)/runs"
```

### Kafka
```bash
kafka-topics.sh --bootstrap-server "$SANCTUM_KAFKA_BOOTSTRAP_SERVERS" --list
kafka-console-producer.sh --bootstrap-server "$SANCTUM_KAFKA_BOOTSTRAP_SERVERS" \
  --topic "$SANCTUM_KAFKA_TOPIC" --producer.config /path/to/producer.properties
kafka-console-consumer.sh --bootstrap-server "$SANCTUM_KAFKA_BOOTSTRAP_SERVERS" \
  --topic "$SANCTUM_KAFKA_TOPIC" --from-beginning --max-messages 1
```

## 7. Required evidence payloads
### GCP example
```json
{
  "capability_id": "security-capability:gcp-platform",
  "target": "project:prod-platform",
  "environment": "prod",
  "source_type": "gcp_api",
  "status": "READY",
  "evidence": {
    "project_id": "prod-platform",
    "resource_inventory": 154,
    "service_accounts": ["svc-sanctum-audit"],
    "iam_model": "organization-level",
    "region": "us-central1"
  }
}
```

### ELK example
```json
{
  "capability_id": "security-capability:observability",
  "target": "elk-cluster",
  "environment": "prod",
  "source_type": "elk_api",
  "status": "READY",
  "evidence": {
    "cluster_status": "green",
    "indices": ["sanctum-events", "sanctum-audit"],
    "search_latency_ms": 120,
    "last_event_at": "2026-10-22T20:15:00Z"
  }
}
```

### Terraform example
```json
{
  "capability_id": "security-capability:terraform-policy",
  "target": "workspace:prod",
  "environment": "prod",
  "source_type": "terraform_api",
  "status": "READY",
  "evidence": {
    "workspace": "prod",
    "drift_detected": false,
    "last_plan_status": "applied",
    "state_hash": "sha256:...",
    "current_resources": 241
  }
}
```

### Kafka example
```json
{
  "event_id": "uuid",
  "schema_version": "sanctum-capability-event-v1",
  "event_type": "security_capability_snapshot",
  "capability_id": "security-capability:kafka-event-bus",
  "target": "broker:prod",
  "environment": "prod",
  "source_type": "kafka_event_bus",
  "status": "READY",
  "payload": {
    "topic": "sanctum.events",
    "partition": 0,
    "offset": 1234,
    "producer": "sanctum-suite"
  }
}
```

## 8. Health and status gates
The capability is `READY` only when all of the following are true:
- [ ] All required env vars are non-empty and valid
- [ ] TLS and CA validation succeed
- [ ] Service accounts / tokens / API keys are valid for target systems
- [ ] API endpoints return HTTP 200 or expected success codes
- [ ] Kafka accepts and reads test events
- [ ] ELK index search returns valid responses
- [ ] Terraform workspace can be enumerated and latest state can be read
- [ ] The observed evidence is written to the normalized capability event schema
- [ ] A policy decision is returned as `allow` by the deployed policy service or gateway

If any check fails, return the capability to `NOT_CONFIGURED` or `PLAN_ONLY` and do not claim live readiness.

## 9. Rollback / fail-safe procedures
- [ ] If GCP auth fails, disable GCP adapter in the runtime config and leave other modules live-ready but disconnected.
- [ ] If ELK is unreachable, keep event indexing in passive mode and do not drop Kafka events permanently without a message retention policy.
- [ ] If Terraform API is unavailable, continue with local state validation only and mark workspace status as degraded.
- [ ] If Kafka brokers fail, route evidence to a local buffer or fail-closed queue with explicit alerting and no silent loss.
- [ ] Record the failed gate, timestamp, and operator decision in the deployment log.

## 10. Sign-off checklist
- [ ] Security owner approved the RBAC model
- [ ] Platform owner approved the endpoints and hostnames
- [ ] Network security approved firewall rules and certificate bindings
- [ ] Operations owner approved health checks and alerting thresholds
- [ ] Evidence schema owner approved the payload definitions
- [ ] Production readiness gate is green for all four systems
- [ ] Runtime status is set to `READY` only after all checks above pass

## 11. Recommended production status summary
The expected post-implementation status is:
- GCP: `READY` if credentials and project metadata pass live validation
- ELK: `READY` if cluster health and index access pass live validation
- Terraform: `READY` if workspace access and state visibility pass live validation
- Kafka: `READY` if broker access, topic ACLs, and event publishing/reading pass live validation

Only this combination should count as the first operational live-ready wave.
