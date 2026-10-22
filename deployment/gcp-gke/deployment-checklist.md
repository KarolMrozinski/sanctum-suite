# GCP GKE deployment checklist

## Cluster
- [ ] GKE cluster exists and is approved
- [ ] Project ID set: `sanctum-prod-482917`
- [ ] Region: `europe-west1`
- [ ] Namespace: `sanctum-phase1`
- [ ] Workload Identity enabled
- [ ] Network policy active

## Access
- [ ] GCP service account and workload identity configured
- [ ] ELK access validated
- [ ] Terraform Cloud access validated
- [ ] Kafka broker ACLs validated

## Operational
- [ ] `SANCTUM_AUTHORIZED_TARGETS` limited to explicit endpoints
- [ ] Secrets managed through GCP Secret Manager or equivalent
- [ ] RBAC is least privilege only
- [ ] Readiness probes green
- [ ] Evidence recorded before promotion to `READY`
