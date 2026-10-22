# Enterprise integrations operations guide

This document summarizes the operational bootstrap for the enterprise modules included in this repository:

- Syslog RFC 5424 and CEF export
- Vault Transit + PKI integration
- Keycloak / OIDC / OAuth2 / SAML federation
- Kubernetes admission webhook validation
- Kafka + Debezium change-data capture

The goal is to provide a minimal, auditable starter configuration suitable for controlled deployments.

## 1. Required production environment

Use a secret manager and TLS-enabled endpoints. Do not store secrets in source control or plain `.env` files in shared environments.

```env
SANCTUM_ENVIRONMENT=production
SANCTUM_API_KEY=replace-with-strong-api-key

SANCTUM_SIEM_WEBHOOK_URL=https://siem.internal.example/events
SANCTUM_SIEM_WEBHOOK_TOKEN=replace-with-a-strong-bearer-token
SANCTUM_SYSLOG_HOST=syslog.internal.example
SANCTUM_SYSLOG_PORT=514
SANCTUM_SYSLOG_PROTOCOL=tcp

SANCTUM_KUBERNETES_WEBHOOK_SECRET=replace-with-shared-secret
SANCTUM_KUBERNETES_WEBHOOK_ALLOWED_GATES=admission.sanctum.local

SANCTUM_KMS_BACKEND=vault-transit
SANCTUM_VAULT_ADDR=https://vault.internal.example:8200
SANCTUM_VAULT_TOKEN_FILE=/run/secrets/vault-token
SANCTUM_VAULT_TRANSIT_MOUNT=transit
SANCTUM_VAULT_TRANSIT_KEY=sanctum-payload
SANCTUM_VAULT_NAMESPACE=security/sanctum
SANCTUM_VAULT_CA_CERT=/etc/sanctum/pki/vault-ca.pem
SANCTUM_PKI_ROLE=sanctum-default
SANCTUM_PKI_TTL=24h

SANCTUM_OIDC_ISSUER=https://keycloak.internal.example/realms/sanctum
SANCTUM_OIDC_AUDIENCE=sanctum-api
SANCTUM_OIDC_CA_CERT=/etc/sanctum/pki/keycloak-ca.pem
SANCTUM_SAML_METADATA_URL=https://keycloak.internal.example/realms/sanctum/protocol/saml/descriptor

SANCTUM_KAFKA_BOOTSTRAP_SERVERS=kafka-1.internal.example:9092,kafka-2.internal.example:9092
SANCTUM_DEBEZIUM_CONNECT_URL=http://debezium-connect.internal.example:8083
SANCTUM_DEBEZIUM_DB_HOST=postgres.internal.example
SANCTUM_DEBEZIUM_DB_NAME=sanctum
SANCTUM_DEBEZIUM_TOPIC_PREFIX=sanctum
SANCTUM_KAFKA_TOPIC=sanctum.events
```

## 2. Vault bootstrap flow

### 2.1 Enable Transit and PKI

```bash
export VAULT_ADDR=https://vault.internal.example:8200
export VAULT_TOKEN="<root-or-admin-token>"

vault secrets enable -path=transit transit
vault write -f transit/keys/sanctum-payload type=aes256-gcm96

vault secrets enable pki
vault secrets tune -max-lease-ttl=8760h pki
vault write pki/root/generate/internal common_name="Sanctum Root CA" ttl=8760h
vault write pki/config/urls issuing_certificates="https://vault.internal.example/v1/pki/ca" \
  crl_distribution_points="https://vault.internal.example/v1/pki/crl"

vault write pki/roles/sanctum-default allowed_domains="internal.example" allow_subdomains=true \
  allow_any_name=false allow_ip_sans=false generate_lease=true ttl="24h"
```

### 2.2 Validate access

```bash
vault read transit/keys/sanctum-payload
vault write -field=certificate pki/issue/sanctum-default common_name="app.internal.example" ttl="24h"
```

## 3. Keycloak bootstrap flow

### 3.1 Create realm and client

1. Log in to Keycloak admin console.
2. Create realm: `sanctum`.
3. Create client: `sanctum-api`.
4. Configure OIDC client settings:
   - Access Type: confidential
   - Standard Flow enabled
   - Service Accounts enabled if machine-to-machine tokens are needed
   - Redirect URIs: trusted application callback endpoints only
5. Add roles:
   - `admin`
   - `auditor`
   - `operator`
6. Map group or role claims in the client mapper to `roles` and tenant id claim (for example `tenant_id`).

### 3.2 OIDC metadata

The application should validate:

- `iss` exactly matches `SANCTUM_OIDC_ISSUER`
- `aud` includes `SANCTUM_OIDC_AUDIENCE`
- HTTPS issuer and CA bundle configured
- tenant and role claims are checked against allowed policy

Example discovery endpoints:

```text
https://keycloak.internal.example/realms/sanctum/.well-known/openid-configuration
https://keycloak.internal.example/realms/sanctum/protocol/saml/descriptor
```

## 4. Kafka + Debezium bootstrap flow

### 4.1 Kafka topics

```bash
kafka-topics --bootstrap-server kafka-1.internal.example:9092 --create --topic sanctum.events --partitions 6 --replication-factor 3
kafka-topics --bootstrap-server kafka-1.internal.example:9092 --create --topic sanctum_connect_configs --partitions 1 --replication-factor 3
kafka-topics --bootstrap-server kafka-1.internal.example:9092 --create --topic sanctum_connect_offsets --partitions 25 --replication-factor 3
kafka-topics --bootstrap-server kafka-1.internal.example:9092 --create --topic sanctum_connect_statuses --partitions 5 --replication-factor 3
```

### 4.2 Debezium PostgreSQL connector

Use a connector JSON payload similar to:

```json
{
  "name": "sanctum-postgres-source",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres.internal.example",
    "database.port": "5432",
    "database.user": "sanctum",
    "database.password": "replace-with-password",
    "database.dbname": "sanctum",
    "database.server.name": "sanctum-db",
    "table.include.list": "public.*",
    "plugin.name": "pgoutput",
    "topic.prefix": "sanctum",
    "slot.name": "sanctum_slot",
    "snapshot.mode": "initial_only",
    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "key.converter.schemas.enable": "false",
    "value.converter.schemas.enable": "false"
  }
}
```

Then register it with the Debezium REST API:

```bash
curl -X POST http://debezium-connect.internal.example:8083/connectors \
  -H 'Content-Type: application/json' \
  -d @debezium-connector.json
```

## 5. Kubernetes webhook operational notes

- Use a shared secret and validate every request signature or HMAC.
- Restrict allowed admission gates to explicit names.
- Reject requests from untrusted namespaces or unexpected API groups.
- Treat webhook response codes as authoritative for enforcement decisions.

Recommended request validation:

```text
SANCTUM_KUBERNETES_WEBHOOK_SECRET=<shared-secret>
SANCTUM_KUBERNETES_WEBHOOK_ALLOWED_GATES=admission.sanctum.local
```

## 6. Monitoring and validation checklist

### Health checks

```bash
curl -fsS https://vault.internal.example:8200/v1/sys/health
curl -fsS https://keycloak.internal.example/realms/sanctum/.well-known/openid-configuration
curl -fsS http://debezium-connect.internal.example:8083/connectors
```

### Log verification

- SIEM: verify CEF and RFC 5424 output and webhook delivery
- Vault: verify transit encryption success and PKI issuance logs
- Keycloak: confirm issuer metadata and realm validation
- Kafka/Debezium: verify connector status and topic replication

## 7. Emergency runbook: certificate, token, and topic rotation

### 7.1 Rotate Vault token and transit key

```bash
# Revoke old token after confirming replacement
vault token revoke <old-token>

# Generate a new root/admin token in a secure secret manager
# Then rotate the app token in the deployment environment
export SANCTUM_VAULT_TOKEN="<new-token>"

# Rotate transit key if the current key is suspected of exposure
vault write -f transit/keys/sanctum-payload/rotate
```

### 7.2 Rotate PKI certificate and CA trust

```bash
# Generate a fresh leaf certificate
vault write -field=certificate pki/issue/sanctum-default common_name="app.internal.example" ttl="24h"

# Replace CA bundle in the host or secret manager
cp vault-ca.pem /etc/sanctum/pki/vault-ca.pem

# Restart the application container so it reloads the trust bundle
docker compose restart sanctum-core
```

### 7.3 Rotate Keycloak/OIDC client secrets and metadata trust

```bash
# In Keycloak admin console:
# 1. regenerate client secret for sanctum-api
# 2. confirm issuer URL unchanged
# 3. rotate CA trust bundle if the IdP cert changed

# Then update the deployment environment and restart the app
export SANCTUM_OIDC_AUDIENCE="sanctum-api"
export SANCTUM_OIDC_CA_CERT="/etc/sanctum/pki/keycloak-ca.pem"
```

### 7.4 Rotate Kafka and Debezium credentials

```bash
# Update Kafka connection secrets in the secret manager
export SANCTUM_KAFKA_BOOTSTRAP_SERVERS="kafka-1.internal.example:9092,kafka-2.internal.example:9092"

# Validate connector health after credentials change
curl -fsS http://debezium-connect.internal.example:8083/connectors/sanctum-postgres-source/status
```

### 7.5 Recovery actions for connector or topic failure

```bash
# Check connector status
curl -fsS http://debezium-connect.internal.example:8083/connectors

# Recreate a connector after config drift
curl -X DELETE http://debezium-connect.internal.example:8083/connectors/sanctum-postgres-source

# Verify Kafka topics are healthy
kafka-topics --bootstrap-server kafka-1.internal.example:9092 --describe --topic sanctum.events
```

## 8. Copy-paste env templates

### 8.1 Staging example

```env
SANCTUM_ENVIRONMENT=staging
SANCTUM_API_KEY=replace-with-staging-key
SANCTUM_SIEM_WEBHOOK_URL=https://siem-staging.internal.example/events
SANCTUM_SIEM_WEBHOOK_TOKEN=replace-with-staging-bearer-token
SANCTUM_SYSLOG_HOST=syslog-staging.internal.example
SANCTUM_SYSLOG_PORT=514
SANCTUM_SYSLOG_PROTOCOL=tcp
SANCTUM_KMS_BACKEND=vault-transit
SANCTUM_VAULT_ADDR=https://vault-staging.internal.example:8200
SANCTUM_VAULT_TOKEN=replace-with-staging-vault-token
SANCTUM_VAULT_TRANSIT_MOUNT=transit
SANCTUM_VAULT_TRANSIT_KEY=sanctum-payload
SANCTUM_OIDC_ISSUER=https://keycloak-staging.internal.example/realms/sanctum
SANCTUM_OIDC_AUDIENCE=sanctum-api
SANCTUM_KAFKA_BOOTSTRAP_SERVERS=kafka:9092
SANCTUM_DEBEZIUM_CONNECT_URL=http://debezium-connect:8083
SANCTUM_DEBEZIUM_DB_HOST=postgres
SANCTUM_DEBEZIUM_DB_NAME=sanctum
SANCTUM_DEBEZIUM_TOPIC_PREFIX=sanctum
```

### 8.2 Production example

```env
SANCTUM_ENVIRONMENT=production
SANCTUM_API_KEY=replace-with-production-api-key
SANCTUM_LICENSE_KEY=replace-with-production-entitlement-key
SANCTUM_SIEM_WEBHOOK_URL=https://siem-prod.internal.example/events
SANCTUM_SIEM_WEBHOOK_TOKEN=replace-with-production-bearer-token
SANCTUM_SYSLOG_HOST=syslog-prod.internal.example
SANCTUM_SYSLOG_PORT=514
SANCTUM_SYSLOG_PROTOCOL=tcp
SANCTUM_KMS_BACKEND=vault-transit
SANCTUM_VAULT_ADDR=https://vault-prod.internal.example:8200
SANCTUM_VAULT_TOKEN=replace-with-production-root-or-approle-token
SANCTUM_VAULT_TRANSIT_MOUNT=transit
SANCTUM_VAULT_TRANSIT_KEY=sanctum-payload
SANCTUM_OIDC_ISSUER=https://keycloak-prod.internal.example/realms/sanctum
SANCTUM_OIDC_AUDIENCE=sanctum-api
SANCTUM_KAFKA_BOOTSTRAP_SERVERS=kafka-prod-1.internal.example:9092,kafka-prod-2.internal.example:9092
SANCTUM_DEBEZIUM_CONNECT_URL=http://debezium-connect-prod.internal.example:8083
SANCTUM_DEBEZIUM_DB_HOST=postgres-prod.internal.example
SANCTUM_DEBEZIUM_DB_NAME=sanctum
SANCTUM_DEBEZIUM_TOPIC_PREFIX=sanctum
```

## 9. Risk and security posture

For production use, keep the following as mandatory operational controls:

- TLS for every external endpoint
- short-lived secrets and rotation automation
- explicit allowlists for webhook gates and callback URIs
- strict tenant and role claim validation
- separate secrets for Vault/Kafka/Keycloak
- audit logging of all certificate issuance and connector changes

This setup is intentionally conservative and aims to keep production trust boundaries explicit rather than permissive.
