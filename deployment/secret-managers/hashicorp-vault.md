# HashiCorp Vault integration

## Recommended pattern
- Enable Kubernetes auth method for the cluster
- Bind dedicated Vault policy to `sanctum-phase1-sa`
- Use Vault Agent Injector or CSI provider

## Example policy
```hcl
path "secret/data/sanctum/phase1/*" {
  capabilities = ["read"]
}
```
