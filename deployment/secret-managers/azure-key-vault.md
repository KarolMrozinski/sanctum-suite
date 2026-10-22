# Azure Key Vault integration

## Recommended pattern
- Enable Azure Workload Identity or managed identity on the cluster
- Grant the workload identity permission to read secrets from the target vault
- Mount secrets using Azure CSI Driver or Key Vault provider

## Example policy
```bash
az keyvault set-policy -n kv-sanctum-prod-01 --secret-permissions get list --spn <APP_ID>
```
