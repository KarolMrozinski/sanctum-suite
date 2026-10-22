# Deployment checklist for GCP / Azure / Kubernetes

## Scope
This checklist is for a real production deployment of the first operational live-ready wave:
- GCP (Google Cloud Platform)
- ELK stack (Elasticsearch / Logstash / Kibana)
- Terraform
- Kafka

The checklist is intentionally strict: no capability moves to `READY` until the runtime has real credentials, endpoint access, RBAC, audit evidence, and health verification.

## 1. Target environment selection

### Option A: GKE (Google Kubernetes Engine)
- [ ] Cluster name: `sanctum-gke-prod`
- [ ] Project ID: `sanctum-prod-482917`
- [ ] Region: `europe-west1`
- [ ] Node pool: `sanctum-workload-pool`
- [ ] Namespace: `sanctum-phase1`
- [ ] Workload identity enabled
- [ ] Private cluster mode enabled if required by policy
- [ ] Network policy enforced

### Option B: AKS (Azure Kubernetes Service)
- [ ] Cluster name: `sanctum-aks-prod`
- [ ] Subscription: `sanctum-prod-sub`
- [ ] Resource group: `rg-sanctum-prod`
- [ ] Region: `westeurope`
- [ ] Namespace: `sanctum-phase1`
- [ ] Managed identity enabled
- [ ] Azure CNI and network policy enabled

## 2. Kubernetes and security baseline
- [ ] Namespace exists: `sanctum-phase1`
- [ ] Service account exists: `sanctum-phase1-sa`
- [ ] Secret exists: `sanctum-phase1-secrets`
- [ ] NetworkPolicy allows only required egress to GCP/Azure providers and internal services
- [ ] Pod security standards are enforced
- [ ] ReadOnlyRootFilesystem enabled
- [ ] Non-root user configured
- [ ] Resource requests/limits defined
- [ ] Liveness and readiness probes configured
- [ ] TLS certs mounted from Kubernetes Secret or external issuer

## 3. GCP readiness checklist
- [ ] `SANCTUM_GCP_PROJECT_ID` set to the production project
- [ ] Service account key or Workload Identity is configured
- [ ] IAM roles are least privilege only
- [ ] Secret manager access is scoped to required secrets
- [ ] Pub/Sub or logging destinations are validated
- [ ] Cloud audit logs are enabled
- [ ] GCP network egress permitted only to approved endpoints

## 4. ELK readiness checklist
- [ ] Elasticsearch endpoint reachable over TLS
- [ ] Username / password or mTLS credentials valid
- [ ] CA certificate trusted by the workload
- [ ] Index permissions scoped to required indices only
- [ ] Logstash pipeline validated with test event
- [ ] Kibana auth and RBAC validated
- [ ] Search and index retention policy reviewed

## 5. Terraform readiness checklist
- [ ] Terraform Cloud / Enterprise org and workspace configured
- [ ] `TERRAFORM_TOKEN` or OIDC federation valid
- [ ] Workspace created: `sanctum-prod-core`
- [ ] VCS integration configured and locked to approved repository
- [ ] Locking, approval, and execution policy validated
- [ ] No broad admin credentials used
- [ ] State backend is protected and encrypted at rest

## 6. Kafka readiness checklist
- [ ] Kafka bootstrap endpoint reachable
- [ ] TLS enabled and CA trusted
- [ ] SASL or mTLS credentials valid
- [ ] Topic ACLs granted only to the required topics
- [ ] Consumer/producer groups named with explicit prefixes
- [ ] Message schema compatibility validated
- [ ] Dead-letter queue or retry policy reviewed

## 7. Required secrets and env vars
- [ ] `SANCTUM_API_KEY`
- [ ] `SANCTUM_AUTHORIZED_TARGETS`
- [ ] `GCP_PROJECT_ID`
- [ ] `GCP_SERVICE_ACCOUNT`
- [ ] `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] `ELASTICSEARCH_URL`
- [ ] `ELASTICSEARCH_USERNAME`
- [ ] `ELASTICSEARCH_PASSWORD`
- [ ] `TERRAFORM_HOSTNAME`
- [ ] `TERRAFORM_ORG`
- [ ] `TERRAFORM_WORKSPACE`
- [ ] `TERRAFORM_TOKEN`
- [ ] `KAFKA_BOOTSTRAP_SERVERS`
- [ ] `KAFKA_SASL_USERNAME`
- [ ] `KAFKA_SASL_PASSWORD`
- [ ] `KAFKA_SECURITY_PROTOCOL`

## 8. Health validation gate
- [ ] GCP API call succeeds with least-privilege service account
- [ ] Elasticsearch index health is green
- [ ] Terraform plan executes successfully in the approved workspace
- [ ] Kafka producer can send a test message to the target topic
- [ ] Kafka consumer can read the same message successfully
- [ ] Evidence object is recorded with status `READY`
- [ ] No module remains in `NOT_CONFIGURED`

## 9. Release approval gate
- [ ] Platform owner sign-off recorded
- [ ] Security owner sign-off recorded
- [ ] Audit/logging owner sign-off recorded
- [ ] Change ticket approved and archived
- [ ] Rollback plan verified

## 10. Example names for production
- Namespace: `sanctum-phase1`
- Service account: `sanctum-phase1-sa`
- Secret: `sanctum-phase1-secrets`
- ConfigMap: `sanctum-phase1-config`
- Role: `sanctum-phase1-reader`
- RoleBinding: `sanctum-phase1-binding`
- Terraform workspace: `sanctum-prod-core`
- Kafka topic prefix: `sanctum.prod`
- ELK index prefix: `sanctum-prod-*`
