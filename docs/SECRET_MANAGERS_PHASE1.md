# Secret manager options for Phase 1

## Recommended default: Azure Key Vault on AKS

### Azure Key Vault
Use Azure Key Vault with the Azure CSI driver or workload identity.

```yaml
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
    userAssignedIdentityID: "<managed-identity-client-id>"
    objects: |
      array:
        - |
          objectName: sanctum-api-key
          secretName: sanctum-api-key
          objectType: secret
        - |
          objectName: gcp-service-account-json
          secretName: gcp-service-account-json
          objectType: secret
        - |
          objectName: elasticsearch-password
          secretName: elasticsearch-password
          objectType: secret
        - |
          objectName: terraform-token
          secretName: terraform-token
          objectType: secret
        - |
          objectName: kafka-password
          secretName: kafka-password
          objectType: secret
  secretObjects:
    - secretName: sanctum-phase1-secrets
      type: Opaque
      data:
        - objectName: sanctum-api-key
          key: SANCTUM_API_KEY
        - objectName: gcp-service-account-json
          key: SANCTUM_GCP_SERVICE_ACCOUNT_JSON
        - objectName: elasticsearch-password
          key: ELASTICSEARCH_PASSWORD
        - objectName: terraform-token
          key: SANCTUM_TERRAFORM_TOKEN
        - objectName: kafka-password
          key: SANCTUM_KAFKA_PASSWORD
```

## Alternative: HashiCorp Vault

### Vault pattern
- Use Kubernetes auth method for service account identity
- Bind a dedicated Vault policy to `sanctum-phase1-sa`
- Retrieve secrets through Vault Agent Injector or Vault CSI Provider
- Keep short-lived tokens and rotate credentials regularly

Example policy excerpt:
```hcl
path "secret/data/sanctum/phase1/*" {
  capabilities = ["read"]
}
```

## Alternative: GCP Secret Manager

### GCP pattern
- Use Workload Identity Federation or a dedicated service account
- Grant `roles/secretmanager.secretAccessor` to the runtime identity
- Mount secret values via the Secret Manager CSI driver or fetch them at startup

Example IAM grant:
```bash
gcloud secrets add-iam-policy-binding sanctum-phase1 --member="serviceAccount:sanctum-phase1-sa@sanctum-prod-482917.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
```

## Deployment rule
The runtime must never read secrets from a Git-tracked file, shell history, or plaintext config manifest. The approved secret manager must inject them into the pod at runtime as files or environment variables only after authorization and rotation policy checks are completed.
