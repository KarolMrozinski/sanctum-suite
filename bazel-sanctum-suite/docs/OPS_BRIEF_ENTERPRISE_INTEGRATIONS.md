# Enterprise Integrations Ops Brief

## Scope

This operations brief covers the enterprise integration modules shipped with SANCTUM-SUITE:

- Syslog RFC 5424 and CEF telemetry export
- Evidence bundle generation for external auditors
- External KMS abstraction with Vault Transit and PKI
- Kubernetes admission webhook handling
- Keycloak / OIDC / OAuth2 / SAML federation
- Kafka + Debezium streaming / CDC integration

These components are intended for governed deployments where trust boundaries, auditability, and explicit configuration are more important than convenience.

## Deployment model

Use the base stack in `docker-compose.yml` and the optional enterprise profile from `docker-compose.override.yml`.

```bash
docker compose --profile enterprise up -d
```

For staging or production, use secret-manager-backed values rather than committing raw credentials to source control.

## Required environment variables

### Core platform

```env
SANCTUM_ENVIRONMENT=production
SANCTUM_API_KEY=replace-with-production-api-key
SANCTUM_LICENSE_KEY=replace-with-entitlement-key
SANCTUM_LICENSE_PUBLIC_KEY=replace-with-public-key
SANCTUM_AUTHORIZED_TARGETS=api.internal.example,auth.internal.example
```

### SIEM and telemetry

```env
SANCTUM_SIEM_WEBHOOK_URL=https://siem.internal.example/events
SANCTUM_SIEM_WEBHOOK_TOKEN=replace-with-bearer-token
SANCTUM_SYSLOG_HOST=syslog.internal.example
SANCTUM_SYSLOG_PORT=514
SANCTUM_SYSLOG_PROTOCOL=tcp
```

### Kubernetes webhook

```env
SANCTUM_KUBERNETES_WEBHOOK_SECRET=replace-with-shared-secret
SANCTUM_KUBERNETES_WEBHOOK_ALLOWED_GATES=admission.sanctum.local
```

### Vault / PKI / KMS

```env
SANCTUM_KMS_BACKEND=vault-transit
SANCTUM_VAULT_ADDR=https://vault.internal.example:8200
SANCTUM_VAULT_TOKEN=replace-with-vault-token
SANCTUM_VAULT_TOKEN_FILE=/run/secrets/vault-token
SANCTUM_VAULT_TRANSIT_MOUNT=transit
SANCTUM_VAULT_TRANSIT_KEY=sanctum-payload
SANCTUM_VAULT_NAMESPACE=security/sanctum
SANCTUM_VAULT_CA_CERT=/etc/sanctum/pki/vault-ca.pem
SANCTUM_PKI_ROLE=sanctum-default
SANCTUM_PKI_TTL=24h
```

### Keycloak / OIDC / SAML

```env
SANCTUM_OIDC_ISSUER=https://keycloak.internal.example/realms/sanctum
SANCTUM_OIDC_AUDIENCE=sanctum-api
SANCTUM_OIDC_CA_CERT=/etc/sanctum/pki/keycloak-ca.pem
SANCTUM_SAML_METADATA_URL=https://keycloak.internal.example/realms/sanctum/protocol/saml/descriptor
```

### Kafka / Debezium

```env
SANCTUM_KAFKA_BOOTSTRAP_SERVERS=kafka-prod-1.internal.example:9092,kafka-prod-2.internal.example:9092
SANCTUM_DEBEZIUM_CONNECT_URL=http://debezium-connect.internal.example:8083
SANCTUM_DEBEZIUM_DB_HOST=postgres.internal.example
SANCTUM_DEBEZIUM_DB_NAME=sanctum
SANCTUM_DEBEZIUM_TOPIC_PREFIX=sanctum
SANCTUM_KAFKA_TOPIC=sanctum.events
```

## Bootstrap checklist

### Vault

1. Enable transit backend.
2. Create or rotate key `sanctum-payload`.
3. Enable PKI and create role `sanctum-default`.
4. Configure trust bundle and CRL endpoint.
5. Confirm app token has least-privilege access.

### Keycloak

1. Create realm `sanctum`.
2. Create client `sanctum-api`.
3. Enable OIDC client credentials / auth code flow as required.
4. Map `roles` and tenant claim to validated tokens.
5. Configure CA and issuer URL trust in the app runtime.

### Kafka and Debezium

1. Create topics for operational events and connector metadata.
2. Register PostgreSQL connector with Debezium.
3. Validate connector health and offset status.
4. Confirm schema compatibility and replication factors are acceptable.

### Kubernetes webhook

1. Set a strong shared secret.
2. Restrict allowed gates to named admission handlers.
3. Validate request signatures before executing policy decisions.
4. Log all denied and approved requests for review.

## Operational runbook

### Rotate Vault token

```bash
vault token revoke <old-token>
export SANCTUM_VAULT_TOKEN="<new-token>"
docker compose restart sanctum-core
```

### Rotate PKI CA trust

```bash
cp vault-ca.pem /etc/sanctum/pki/vault-ca.pem
docker compose restart sanctum-core
```

### Rotate Keycloak client secret

1. Regenerate secret in Keycloak admin console.
2. Update `SANCTUM_OIDC_*` values in the deployment environment.
3. Restart the service or rollout a new container instance.

### Rotate SIEM webhook token

```bash
export SANCTUM_SIEM_WEBHOOK_TOKEN="<new-bearer-token>"
docker compose restart sanctum-core
```

### Rotate Kafka credentials or cluster endpoints

```bash
export SANCTUM_KAFKA_BOOTSTRAP_SERVERS="kafka-1.internal.example:9092,kafka-2.internal.example:9092"
curl -fsS http://debezium-connect.internal.example:8083/connectors
```

### Recover connector health

```bash
curl -fsS http://debezium-connect.internal.example:8083/connectors
curl -fsS http://debezium-connect.internal.example:8083/connectors/sanctum-postgres-source/status
```

## Security controls

Mandatory controls for production environments:

- TLS everywhere for external services
- secret manager or mounted secret files, never plaintext source control files
- short-lived credential rotation and automation
- enforce exact issuer / audience values
- strict allowlists for webhook gates and callback URLs
- separate credentials per integration boundary
- audit logs for Vault issuance, Keycloak changes, and Debezium connector state

## Recommended alerting

Monitor the following events:

- failed webhook POSTs to SIEM endpoints
- Vault token or PKI issuance errors
- OIDC validation failures and issuer mismatch
- Kafka broker connectivity loss
- Debezium connector task failures or offset lag
- Kubernetes admission webhook denial spikes

## Summary

This integration set is designed to provide enterprise logging, identity, key management, and event-streaming capabilities in a clearly bounded and auditable manner. Production use should rely on explicit trust configuration, strong secret rotation, and operational visibility rather than implicit defaults.
