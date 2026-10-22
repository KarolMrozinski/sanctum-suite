# Azure AKS deployment checklist

## Cluster
- [ ] Subscription selected: `sanctum-prod-sub`
- [ ] Resource group created: `rg-sanctum-prod`
- [ ] AKS cluster present: `sanctum-aks-prod`
- [ ] Region: `westeurope`
- [ ] Namespace: `sanctum-phase1`
- [ ] Managed identity enabled
- [ ] Azure Policy / Defender reviewed

## Namespace and identity
- [ ] Namespace created
- [ ] Service account created: `sanctum-phase1-sa`
- [ ] Role created: `sanctum-phase1-reader`
- [ ] RoleBinding created: `sanctum-phase1-binding`
- [ ] Secret created: `sanctum-phase1-secrets`
- [ ] ConfigMap created: `sanctum-phase1-config`

## Secret manager
- [ ] Azure Key Vault or targeted secret backend selected
- [ ] Managed identity has access to required secrets
- [ ] Secret names are mapped to Kubernetes Secret entries
- [ ] Rotation policy verified

## Runtime
- [ ] `SANCTUM_API_KEY` set
- [ ] `GCP_PROJECT_ID` set
- [ ] `ELASTICSEARCH_URL` set
- [ ] `TERRAFORM_HOSTNAME` set
- [ ] `TERRAFORM_TOKEN` set
- [ ] `KAFKA_BOOTSTRAP_SERVERS` set
- [ ] `KAFKA_SASL_USERNAME` and password set
- [ ] `SANCTUM_AUTHORIZED_TARGETS` set to approved endpoints only

## Validation
- [ ] GCP API access success
- [ ] ELK readiness success
- [ ] Terraform workspace access success
- [ ] Kafka producer/consumer success
- [ ] Health endpoint returns live status
- [ ] Final state is `READY` only after evidence is stored
