# Production Runbook: all live-ready phases

## Purpose
This runbook covers the complete phased rollout model for SANCTUM-SUITE and defines the operational gate for moving a module from `NOT_CONFIGURED` to `READY`.

The phases are:
- Phase 1: GCP + ELK + Terraform + Kafka
- Phase 2: BAM + HIRS + paccor + RIM
- Phase 3: legacy host baselines + embedded systems + graph/agentic AI + QKD + neuromorphic compute
- Phase 4: mission, collection intelligence, and AI governance
- Phase 5: signal fusion, data governance, retention, and final operational audit
- Phase 6: compliance cutover and control assurance

Critical rule: no adapter is considered live-ready unless there are real endpoint values, real auth, real RBAC/ACL, a real health check, and policy validation.

## Phase 1: GCP + ELK + Terraform + Kafka
### Required env vars
- `SANCTUM_GCP_PROJECT_ID`
- `SANCTUM_GCP_REGION`
- `SANCTUM_GCP_SERVICE_ACCOUNT`
- `SANCTUM_GCP_SERVICE_ACCOUNT_JSON`
- `SANCTUM_ELK_ENDPOINT`
- `SANCTUM_ELK_API_KEY` or `SANCTUM_ELK_USERNAME` + `SANCTUM_ELK_PASSWORD`
- `SANCTUM_ELK_INDEX_PATTERN`
- `SANCTUM_TERRAFORM_API_URL`
- `SANCTUM_TERRAFORM_ORG`
- `SANCTUM_TERRAFORM_WORKSPACE`
- `SANCTUM_TERRAFORM_TOKEN`
- `SANCTUM_KAFKA_BOOTSTRAP_SERVERS`
- `SANCTUM_KAFKA_TOPIC`
- `SANCTUM_KAFKA_USERNAME`
- `SANCTUM_KAFKA_PASSWORD`
- `SANCTUM_AUTHORIZED_TARGETS`

### Gate checklist
- [ ] GCP project exists and is reachable
- [ ] GCP service account has least-privilege IAM
- [ ] ELK cluster health is green
- [ ] ELK index access is valid
- [ ] Terraform workspace is reachable
- [ ] Terraform runs/state metadata are readable
- [ ] Kafka brokers respond and topic exists
- [ ] Kafka producer/consumer ACLs pass
- [ ] Capability event is emitted and published
- [ ] Event is searchable in ELK
- [ ] Policy evaluation returns allow

## Phase 2: BAM + HIRS + paccor + RIM
### Required env vars
- `SANCTUM_BAM_METADATA_PATH`
- `SANCTUM_BAM_API_TOKEN`
- `SANCTUM_HIRS_API_URL`
- `SANCTUM_HIRS_API_TOKEN`
- `SANCTUM_PACCOR_CERT_SUBJECT`
- `SANCTUM_PACCOR_API_URL`
- `SANCTUM_PACCOR_TOKEN`
- `SANCTUM_RIM_MANIFEST_PATH`
- `SANCTUM_RIM_API_URL`
- `SANCTUM_RIM_TOKEN`

### Gate checklist
- [ ] BAM metadata source is available and checksum validated
- [ ] HIRS attestation endpoint is reachable and returns a signed attestation
- [ ] Paccor certificate service can issue a valid certificate subject
- [ ] RIM manifest is readable and signed/verified
- [ ] Output is bound to the target host or platform identity
- [ ] Policy permit is granted for evidence ingestion

## Phase 3: legacy hosts + embedded + AI/graph + QKD + neuromorphic
### Required env vars
- `SANCTUM_HOST_INVENTORY_URL`
- `SANCTUM_HOST_API_TOKEN`
- `SANCTUM_OS_FAMILY`
- `SANCTUM_VXWORKS_API_URL`
- `SANCTUM_VXWORKS_TOKEN`
- `SANCTUM_GNN_MODEL_REGISTRY`
- `SANCTUM_MODEL_API_TOKEN`
- `SANCTUM_AGENT_RUNTIME`
- `SANCTUM_AGENT_TOKEN`
- `SANCTUM_QKD_PEER_ID`
- `SANCTUM_QKD_KME_URL`
- `SANCTUM_QKD_TOKEN`
- `SANCTUM_NEUROMORPHIC_ACCELERATOR`
- `SANCTUM_NEUROMORPHIC_TOKEN`

### Gate checklist
- [ ] Host inventory service is reachable
- [ ] Legacy OS baseline is approved by the environment owner
- [ ] VxWorks or embedded API responds with signed device or firmware metadata
- [ ] Model registry can resolve the target artifact or graph model
- [ ] Agent runtime is authenticated and isolated by tenant or workload
- [ ] QKD KME is reachable and session is bound to a valid peer ID
- [ ] Neuromorphic accelerator metadata is available and policy-approved
- [ ] Run results are traceable to evidence schema and signed output

## Phase 4: mission / collection / AI governance
### Required env vars
- `SANCTUM_XKEYSCORE_API_URL`
- `SANCTUM_XKEYSCORE_TOKEN`
- `SANCTUM_BOUNDLESS_API_URL`
- `SANCTUM_BOUNDLESS_TOKEN`
- `SANCTUM_MISSION_API_URL`
- `SANCTUM_MISSION_API_TOKEN`
- `SANCTUM_SEC_PALM_MODEL_REGISTRY`
- `SANCTUM_MODEL_REGISTRY_URL`
- `SANCTUM_MODEL_GOVERNANCE_TOKEN`
- `SANCTUM_PALANTIR_FOUNDRY_API_URL`
- `SANCTUM_DATA_FUSION_URL`
- `SANCTUM_DATA_FUSION_TOKEN`

### Gate checklist
- [ ] Mission telemetry endpoint is reachable
- [ ] Collection system is authorized for the target scope and tenant
- [ ] Model registry is approved and policy-allowed for production inference or governance review
- [ ] Graph/foundry integration is accessible and auth-validated
- [ ] No unauthorized cross-tenant data flow occurs
- [ ] Data lineage and signatures are maintained

## Phase 5: retention / operational audit / compliance cutover
### Required env vars
- `SANCTUM_RETENTION_POLICY_DB`
- `SANCTUM_AUDIT_LOG_STORE_URL`
- `SANCTUM_AUDIT_LOG_TOKEN`
- `SANCTUM_COMPLIANCE_FRAMEWORK`
- `SANCTUM_COMPLIANCE_API_URL`
- `SANCTUM_COMPLIANCE_TOKEN`

### Gate checklist
- [ ] Retention policy database is writable and backed by durable storage
- [ ] Audit log store accepts signed telemetry records
- [ ] Compliance framework and controls are mapped to the target environment
- [ ] Retention and deletion policies are tested in a dry-run mode
- [ ] Audit evidence matches required control objective and log retention period
- [ ] Final governance sign-off is recorded

## Shared production gate
For every phase:
- [ ] All env vars are set in the secret manager, not in Git
- [ ] Target hostnames are explicitly allowlisted in `SANCTUM_AUTHORIZED_TARGETS`
- [ ] TLS/mTLS certificates are valid and trusted
- [ ] RBAC/ACL is least privilege and approved
- [ ] API returns success and valid evidence payload
- [ ] Normalized evidence schema is produced
- [ ] Policy service permits the request
- [ ] Runtime status is `READY` only after a live check passes

## Approval and sign-off template
- Security owner: ________
- Platform owner: ________
- Network owner: ________
- Operations owner: ________
- Compliance owner: ________
- Date / time: ________
- Final status: `READY` / `NOT_CONFIGURED` / `PLAN_ONLY`

## Rollback policy
If a phase fails any gate, keep the system in `PLAN_ONLY` or `NOT_CONFIGURED` and do not expose live data movement. The deployment is considered failed until all required checks are complete.
