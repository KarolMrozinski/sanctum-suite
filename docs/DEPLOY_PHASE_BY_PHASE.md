# Deployment plan: phase by phase with real namespace and service account names

## Phase 1: GCP + ELK + Terraform + Kafka

### Target namespace and identities
- Namespace: `sanctum-phase1`
- Service account: `sanctum-phase1-sa`
- Secret: `sanctum-phase1-secrets`
- ConfigMap: `sanctum-phase1-config`
- Role: `sanctum-phase1-reader`
- RoleBinding: `sanctum-phase1-binding`
- NetworkPolicy: `sanctum-phase1-default-deny`

### Required runtime dependencies
- GCP project: `sanctum-prod-482917`
- GKE cluster: `sanctum-gke-prod`
- ELK endpoint: `https://elasticsearch.internal.example:9200`
- Kafka brokers: `kafka-bootstrap.sanctum-phase1.svc.cluster.local:9093`
- Terraform workspace: `sanctum-prod-core`

### Deployment steps
1. Create namespace: `kubectl create namespace sanctum-phase1`
2. Create service account: `sanctum-phase1-sa`
3. Create secret: `sanctum-phase1-secrets` with GCP, ELK, Terraform, and Kafka credentials
4. Configure RBAC with least privilege for reading ConfigMaps, Secrets, and API access
5. Apply the Phase 1 Deployment and NetworkPolicy
6. Validate GCP access, ELK health, Terraform workspace plan, and Kafka topic write/read test
7. Set state to `READY` only after health checks succeed and evidence is recorded

## Phase 2: BAM + HIRS + paccor + RIM

### Target namespace and identities
- Namespace: `sanctum-phase2`
- Service account: `sanctum-phase2-sa`
- Secret: `sanctum-phase2-secrets`
- ConfigMap: `sanctum-phase2-config`
- Role: `sanctum-phase2-attestation-reader`

### Required runtime dependencies
- BAM metadata path: `/opt/sanctum/bam/metadata`
- HIRS endpoint: `https://hirs.internal.example/api/v1/attest`
- paccor endpoint: `https://paccor.internal.example/api/v1/certificates`
- RIM manifest path: `/opt/sanctum/rim/manifest.json`

### Deployment steps
1. Create namespace `sanctum-phase2`
2. Add service account `sanctum-phase2-sa`
3. Load BAM/HIRS/paccor/RIM credentials into `sanctum-phase2-secrets`
4. Apply attestation and manifest validation jobs
5. Verify metadata integrity and attestation claims
6. Promote only after a live health check and signed evidence generation

## Phase 3: legacy hosts + embedded + AI / graph + QKD + neuromorphic

### Target namespace and identities
- Namespace: `sanctum-phase3`
- Service account: `sanctum-phase3-sa`
- Secret: `sanctum-phase3-secrets`
- ConfigMap: `sanctum-phase3-config`
- Role: `sanctum-phase3-legacy-reader`

### Required runtime dependencies
- Host inventory endpoint: `https://host-inventory.internal.example/api/v1/hosts`
- VxWorks endpoint: `https://vxworks.internal.example:8443`
- GNN model registry: `https://gnn.internal.example/api/v1/models`
- Agent runtime: `https://agent-runtime.internal.example/api/v1/status`
- QKD peer: `https://qkd-gateway.internal.example`
- Neuromorphic endpoint: `https://loihi.internal.example/api/v1/diagnostics`

### Deployment steps
1. Create namespace `sanctum-phase3`
2. Create dedicated secret and service account for legacy and embedded host access
3. Validate host baselines and embedded endpoint trust chains
4. Deploy graph/AI runtime model registration checks
5. Validate QKD session state and neuromorphic hardware metadata access
6. Enable only after policy approvals and evidence collection

## Phase 4: mission / signals / governance

### Target namespace and identities
- Namespace: `sanctum-phase4`
- Service account: `sanctum-phase4-sa`
- Secret: `sanctum-phase4-secrets`
- ConfigMap: `sanctum-phase4-config`
- Role: `sanctum-phase4-mission-reader`

### Required runtime dependencies
- XKeyscore endpoint: `https://signals.internal.example/api/v1/query`
- Boundless Informant endpoint: `https://collection.internal.example/api/v1/status`
- Mission API: `https://mission.internal.example/api/v1/current`
- Data governance endpoint: `https://governance.internal.example/api/v1/models`

### Deployment steps
1. Create namespace `sanctum-phase4`
2. Grant least-privilege access for mission and signals workloads
3. Validate collection and mission API auth and tenant boundaries
4. Test governance model lineage and approvals
5. Only then promote to `READY`

## Phase 5: retention / audit / compliance

### Target namespace and identities
- Namespace: `sanctum-phase5`
- Service account: `sanctum-phase5-sa`
- Secret: `sanctum-phase5-secrets`
- ConfigMap: `sanctum-phase5-config`
- Role: `sanctum-phase5-audit-reader`

### Required runtime dependencies
- Audit log sink: `https://audit.internal.example/api/v1/events`
- Retention policy DB: `sanctum-retention-db`
- Compliance API: `https://compliance.internal.example/api/v1/checks`

### Deployment steps
1. Create namespace `sanctum-phase5`
2. Configure durable retention store and audit sink
3. Test policy enforcement with dry-run scenarios
4. Validate evidence retention and compliance checks
5. Approve final cutover after sign-off from security and compliance owners

## Phase 6: production cutover

### Target namespace and identities
- Namespace: `sanctum-phase6`
- Service account: `sanctum-phase6-sa`
- Secret: `sanctum-phase6-secrets`
- ConfigMap: `sanctum-phase6-config`
- Role: `sanctum-phase6-ops-reader`

### Required runtime dependencies
- Final production environment values from all previous phases
- Approved RBAC, network policy, and secret rotation procedures
- Final evidence store and alerting 

### Deployment steps
1. Confirm all prior phases are green
2. Validate environment-specific RBAC and network policy
3. Perform final production sign-off
4. Enable live operational mode
5. Record final production readiness in the evidence system

## Operational rollout rule
No phase should move to `READY` until:
- environment variables are present
- service account is valid
- RBAC is least privilege
- endpoint health is green
- evidence is recorded
- security and platform owners approve the change

## Recommended command sequence
```bash
kubectl create namespace sanctum-phase1
kubectl create sa sanctum-phase1-sa -n sanctum-phase1
kubectl create secret generic sanctum-phase1-secrets -n sanctum-phase1 --from-env-file=.env.phase1.gcp.example
kubectl apply -f k8s/phase1-live-ready.yaml
kubectl -n sanctum-phase1 get pods
kubectl -n sanctum-phase1 logs deploy/sanctum-suite-phase1
```
