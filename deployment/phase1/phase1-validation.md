# Phase 1 validation

## Commands
```bash
kubectl -n sanctum-phase1 get pods
kubectl -n sanctum-phase1 logs deploy/sanctum-suite-phase1
kubectl -n sanctum-phase1 get rolebinding sanctum-phase1-binding
curl -k https://localhost:8000/healthz
```

## Ready gate
Only proceed when:
- GCP access works
- ELK health passes
- Terraform workspace access succeeds
- Kafka test event passes
- audit evidence is recorded
- no unresolved security findings remain
