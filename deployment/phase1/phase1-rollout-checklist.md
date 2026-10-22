# Phase 1 rollout checklist

- [ ] Namespace exists: `sanctum-phase1`
- [ ] Service account exists: `sanctum-phase1-sa`
- [ ] Role exists: `sanctum-phase1-reader`
- [ ] RoleBinding exists: `sanctum-phase1-binding`
- [ ] Secret exists: `sanctum-phase1-secrets`
- [ ] ConfigMap exists: `sanctum-phase1-config`
- [ ] GCP credentials validated
- [ ] ELK endpoint validated
- [ ] Terraform workspace validated
- [ ] Kafka producer/consumer validated
- [ ] Health check green
- [ ] Promotion to `READY` approved by security owner
