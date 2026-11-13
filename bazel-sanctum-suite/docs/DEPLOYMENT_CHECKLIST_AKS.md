# Azure AKS deployment checklist for Phase 1

## Scope
This checklist is for the first production-ready operational wave in Azure Kubernetes Service (AKS):
- Azure Key Vault or external secret store
- GCP platform telemetry integration
- ELK stack telemetry
- Terraform Enterprise / Terraform Cloud access
- Kafka broker access

## 1. Cluster and project setup
- [ ] Subscription: `sanctum-prod-sub`
- [ ] Resource group: `rg-sanctum-prod`
- [ ] AKS cluster: `sanctum-aks-prod`
- [ ] Region: `westeurope`
- [ ] Namespace: `sanctum-phase1`
- [ ] Node pool: `systempool` or `sanctum-workload-pool`
- [ ] Azure CNI enabled
- [ ] Azure Policy / Azure Defender review complete
- [ ] Managed Identity enabled

## 2. Namespaces and identities
- [ ] Namespace created: `sanctum-phase1`
- [ ] Service account created: `sanctum-phase1-sa`
- [ ] Role created: `sanctum-phase1-reader`
- [ ] RoleBinding created: `sanctum-phase1-binding`
- [ ] Secret created: `sanctum-phase1-secrets`
- [ ] ConfigMap created: `sanctum-phase1-config`

## 3. Secret manager integration
### Azure Key Vault
- [ ] Key Vault name: `kv-sanctum-prod-01`
- [ ] CSI driver installed and enabled on AKS
- [ ] Managed Identity has access to the Key Vault
- [ ] Secret names mapped to Kubernetes Secret objects
- [ ] Rotation policy configured
- [ ] No raw secrets in Git or Docker build context

### HashiCorp Vault
- [ ] Vault address configured and TLS verified
- [ ] Kubernetes auth method enabled for the cluster
- [ ] Service account role bound to appropriate Vault policy
- [ ] Token TTL short-lived and rotation enabled

### GCP Secret Manager
- [ ] Workload Identity Federation or service account configured
- [ ] Secret access scoped to only required values
- [ ] Secret version rotation policy enabled

## 4. Required env vars
- [ ] `SANCTUM_ENVIRONMENT=production`
- [ ] `SANCTUM_NAMESPACE=sanctum-phase1`
- [ ] `SANCTUM_API_KEY`
- [ ] `SANCTUM_AUTHORIZED_TARGETS`
- [ ] `GCP_PROJECT_ID`
- [ ] `GCP_REGION`
- [ ] `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] `ELASTICSEARCH_URL`
- [ ] `ELASTICSEARCH_USERNAME`
- [ ] `ELASTICSEARCH_PASSWORD`
- [ ] `TERRAFORM_HOSTNAME`
- [ ] `TERRAFORM_ORG`
- [ ] `TERRAFORM_WORKSPACE`
- [ ] `TERRAFORM_TOKEN`
- [ ] `KAFKA_BOOTSTRAP_SERVERS`
- [ ] `KAFKA_SECURITY_PROTOCOL`
- [ ] `KAFKA_SASL_USERNAME`
- [ ] `KAFKA_SASL_PASSWORD`

## 5. Network and RBAC policy
- [ ] Egress restricted to approved endpoints
- [ ] Only required ports are open
- [ ] NetworkPolicy allows GCP, ELK, Terraform, Kafka endpoints only
- [ ] Role has read-only access to ConfigMaps/Secrets required for runtime
- [ ] No broad cluster-admin rights granted

## 6. Health validation gates
- [ ] GCP API call succeeds using least-privilege credentials
- [ ] ELK node health passes and index is writable
- [ ] Terraform plan / workspace access works in target environment
- [ ] Kafka producer sends test event successfully
- [ ] Kafka consumer reads the same event successfully
- [ ] SANCTUM status becomes `READY` only after evidence is recorded

## 7. Example production names
- Namespace: `sanctum-phase1`
- Service account: `sanctum-phase1-sa`
- Secret: `sanctum-phase1-secrets`
- ConfigMap: `sanctum-phase1-config`
- Role: `sanctum-phase1-reader`
- RoleBinding: `sanctum-phase1-binding`
- NetworkPolicy: `sanctum-phase1-default-deny`
- Azure Key Vault: `kv-sanctum-prod-01`
