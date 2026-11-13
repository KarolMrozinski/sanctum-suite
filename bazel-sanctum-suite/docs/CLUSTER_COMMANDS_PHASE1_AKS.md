# Cluster commands for AKS Phase 1 deployment

## 1. Create the namespace, service account, and role
```bash
az login
az account set --subscription sanctum-prod-sub
az aks get-credentials --resource-group rg-sanctum-prod --name sanctum-aks-prod --overwrite-existing

kubectl create namespace sanctum-phase1
kubectl -n sanctum-phase1 create serviceaccount sanctum-phase1-sa
kubectl -n sanctum-phase1 create role sanctum-phase1-reader --verb=get,list,watch --resource=configmaps,secrets,pods
kubectl -n sanctum-phase1 create rolebinding sanctum-phase1-binding --role=sanctum-phase1-reader --serviceaccount=sanctum-phase1:sanctum-phase1-sa
```

## 2. Create the Kubernetes Secret from a local file
```bash
kubectl -n sanctum-phase1 create secret generic sanctum-phase1-secrets \
  --from-env-file=.env.phase1.gcp.example
```

## 3. Create TLS CA cert secrets
```bash
kubectl -n sanctum-phase1 create secret generic sanctum-phase1-certs \
  --from-file=elk-ca.pem=./secrets/elk-ca.pem \
  --from-file=terraform-ca.pem=./secrets/terraform-ca.pem \
  --from-file=kafka-ca.pem=./secrets/kafka-ca.pem
```

## 4. Apply the Phase 1 deployment
```bash
kubectl apply -f k8s/phase1-live-ready-aks.yaml
kubectl -n sanctum-phase1 get pods
kubectl -n sanctum-phase1 get svc
kubectl -n sanctum-phase1 describe deployment sanctum-suite-phase1
```

## 5. Validate runtime health
```bash
kubectl -n sanctum-phase1 logs deploy/sanctum-suite-phase1
kubectl -n sanctum-phase1 port-forward svc/sanctum-suite-phase1 8000:80
curl -k https://localhost:8000/healthz
```

## 6. Optional: integrate Azure Key Vault CSI
```bash
kubectl apply -f - <<'YAML'
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: sanctum-phase1-secrets
  namespace: sanctum-phase1
spec:
  provider: azure
  parameters:
    keyvaultName: "kv-sanctum-prod-01"
    usePodIdentity: "false"
    useVMManagedIdentity: "true"
    objects: |
      array:
        - |
          objectName: sanctum-api-key
          secretName: sanctum-api-key
          objectType: secret
  secretObjects:
    - secretName: sanctum-phase1-secrets
      type: Opaque
      data:
        - objectName: sanctum-api-key
          key: SANCTUM_API_KEY
YAML
```

## 7. Rollback / cleanup
```bash
kubectl -n sanctum-phase1 delete deployment sanctum-suite-phase1
kubectl -n sanctum-phase1 delete secret sanctum-phase1-secrets sanctum-phase1-certs
kubectl delete namespace sanctum-phase1
```

## 8. Real readiness gate
Only set the environment to `READY` after:
- GCP API call succeeds with least-privilege auth
- Elasticsearch health is green
- Terraform workspace access is valid
- Kafka producer/consumer test passes
- audit evidence is stored
- security and platform owners approve the release
