# Customer Installation and Deployment

This guide describes a local evaluation setup. Confirm that your license authorizes installation and use before proceeding; the repository license requires written permission for execution and commercial deployment.

## Requirements

- Python 3.11 or newer
- Node.js version supported by the dashboard's Next.js release
- npm
- A supported environment for the modules you intend to use
- Written authorization to test any targets or systems

## Install the Python application

From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
sanctum --help
```

Run the test suite before evaluation:

```powershell
python -m pytest -q
```

The API server starts on loopback by default:

```powershell
$env:SANCTUM_API_KEY = python -c "import secrets; print(secrets.token_urlsafe(48))"
sanctum serve --host 127.0.0.1 --port 8000
```

In legacy single-operator mode, the API rejects protected requests and fails readiness unless `SANCTUM_API_KEY` is configured with at least 32 bytes. The SDK reads this variable by default; alternatively pass `api_key` explicitly. Do not store a production key in source control or a checked-in `.env` file.

### Vault Transit key management

The local ephemeral encryption backend is for development only: generated envelopes cannot be decrypted after the process restarts. Production and air-gapped preflight require the HashiCorp Vault Transit backend; the application fails closed rather than silently using an ephemeral key.

Provision a Transit mount and encryption key through the organization's Vault administration process. Give the application identity only the required `update` capability on that key's `encrypt` and `decrypt` paths; do not grant key-management or mount-administration capabilities. Provide the Vault token through a protected file or deployment secret manager, and install the Vault CA in the host trust store or point `SANCTUM_VAULT_CA_CERT` at its trusted CA bundle. TLS verification cannot be disabled.

```powershell
$env:SANCTUM_ENVIRONMENT = "air-gapped"
$env:SANCTUM_KMS_BACKEND = "vault-transit"
$env:SANCTUM_VAULT_ADDR = "https://vault.internal.example:8200"
$env:SANCTUM_VAULT_TOKEN_FILE = "C:\secure\vault-token"
$env:SANCTUM_VAULT_TRANSIT_MOUNT = "transit"
$env:SANCTUM_VAULT_TRANSIT_KEY = "sanctum-payload"
$env:SANCTUM_VAULT_CA_CERT = "C:\secure\vault-ca.pem"
$env:SANCTUM_AUDIT_S3_ENDPOINT = "https://minio.internal.example"
$env:SANCTUM_AUDIT_S3_BUCKET = "sanctum-audit-worm"
$env:SANCTUM_AUDIT_S3_ACCESS_KEY_FILE = "C:\secure\minio-access-key"
$env:SANCTUM_AUDIT_S3_SECRET_ACCESS_KEY_FILE = "C:\secure\minio-secret-key"
$env:SANCTUM_AUDIT_S3_CA_CERT = "C:\secure\minio-ca.pem"
$env:SANCTUM_AUDIT_PSEUDONYM_KEY_FILE = "C:\secure\audit-pseudonym.key"
```

Vault Transit stores and rotates the key; payload envelopes contain the Vault ciphertext and key name, not a locally wrapped DEK. Vault availability and Transit policy are required for decryption. Back up and test recovery of Vault's key material according to the organization's approved procedure. This helper encrypts only payloads explicitly passed to it; it does not encrypt SQLite/tenant databases, reports, local logs, or backups. Protect those separately with approved storage encryption and tested encrypted backups. Do not reuse keys across environments or treat a successful encryption call as proof of HSM use, FIPS validation, or compliance. The production preflight performs a test encrypt/decrypt round trip, which verifies current connectivity and key permissions only; it does not prove backup recovery or deployment security.

### MinIO immutable access audit

Production/air-gapped deployments require the external audit store for protected API routes. Set `SANCTUM_IMMUTABLE_AUDIT_ENABLED=true` and configure a dedicated MinIO bucket with versioning and Object Lock enabled. Use a dedicated service account limited to bucket versioning/Object Lock reads and `PutObject`/`GetObjectRetention` on the `api-access/` prefix; provide its credentials through protected secret files (`SANCTUM_AUDIT_S3_ACCESS_KEY_FILE` and `SANCTUM_AUDIT_S3_SECRET_ACCESS_KEY_FILE`) or a deployment secret manager. Configure MinIO with trusted HTTPS and, for a private CA, set `SANCTUM_AUDIT_S3_CA_CERT`. TLS verification cannot be disabled.

Create a dedicated random pseudonymization key of at least 32 bytes (for example, `openssl rand -out /secure/audit-pseudonym.key 32`), store it in the approved secret manager, and provide it as `SANCTUM_AUDIT_PSEUDONYM_KEY_FILE`. This key is distinct from Vault Transit and report-signing keys. Readiness fails if it is missing or unreadable. The API uses keyed HMAC-SHA-256 with separate subject/tenant namespaces before writing identity metadata to local or immutable access-audit records; raw OIDC subject and tenant claims are not written to those access-audit fields. Keep the key under controlled backup and rotation: changing it prevents correlating newly generated pseudonyms with records made using the old key.

The application verifies versioning and Object Lock at initialization and applies `COMPLIANCE` retention for seven years to each request-start and request-completion record. Production preflight writes and verifies a permanently retained canary object. The selected `fail-closed` policy records a minimal request-start event before a protected route runs; if that write fails, the route is not executed. Completion is written separately after the route. If that second write fails, the client receives HTTP 503 and the operation's outcome may be uncertain; the start record remains in WORM. Provision alerts and an operator recovery procedure for this state.

Records contain a request ID, method, route template/group, response code, authentication method, timestamp, a SHA-256 credential fingerprint, and keyed pseudonyms for subject and tenant in production. Pseudonyms support correlation but are not anonymous; do not treat them as permission to store classified content. Records do not contain request/response bodies, query strings, client IP addresses, or raw identity claims. This audit feature is not approval to store classified information: keep classified payloads and identifying evidence outside SANCTUM-SUITE unless the deployment has received the required independent authorization/accreditation. The seven-year Compliance lock prevents early deletion; confirm legal retention, privacy obligations, encryption-at-rest, backup, access, and destruction requirements before deployment.

### OIDC users, roles, and tenant-scoped data

For user authentication, configure both `SANCTUM_OIDC_ISSUER` (HTTPS) and `SANCTUM_OIDC_AUDIENCE`. The API validates RS256/ES256 access-token signatures using HTTPS OIDC discovery and cached JWKS, then checks issuer, audience, subject, expiration, issue time, and not-before. Key IDs are refreshed once when an unknown signing key is received. For a private Keycloak CA, install it in the host trust store or set `SANCTUM_OIDC_CA_CERT` to its trusted CA bundle; TLS verification cannot be disabled. Air-gapped network policy must allow only the configured Keycloak issuer and JWKS endpoints. The token must include a string or string-array role claim (`SANCTUM_OIDC_ROLES_CLAIM`, default `roles`) containing `ADMIN`, `AUDITOR`, or `VIEWER`, and a tenant identifier claim (`SANCTUM_OIDC_TENANT_CLAIM`, default `tenant_id`). Claims are case-insensitive for role names. Map the issuer's groups/roles and immutable tenant identifier deliberately; an arbitrary display name is not a tenant boundary.

For Keycloak, configure an API audience mapper for the exact `SANCTUM_OIDC_AUDIENCE`; add protocol mappers that emit the trusted role list and immutable tenant ID as the flat claims named above. Restrict these mappers to access tokens issued for this API, and do not derive the tenant claim from user-editable profile fields. In production/air-gapped mode OIDC is mandatory and legacy shared API-key authentication is rejected, including when `SANCTUM_ALLOW_LEGACY_API_KEY=true`.

Production API startup also requires an operator-managed RSA report-signing key pair through `SANCTUM_REPORT_SIGNING_PRIVATE_KEY_FILE` and `SANCTUM_REPORT_SIGNING_PUBLIC_KEY_FILE`. The pair must match; production does not generate report-signing keys. The private PEM must be readable by the service without an interactive passphrase, so mount it only as a protected runtime secret and control its access/backup/rotation. Development-only `.keys` auto-generation is not a production trust anchor.

`ADMIN` can use the supported tenant-scoped API; `AUDITOR` can read and modify cases, playbooks, and control assessments; `VIEWER` is read-only. The legacy `/api/v1/audit` and `/api/v1/analytics` endpoints are denied to OIDC identities because their underlying report/analytics stores are not tenant-scoped. They remain available only through the legacy shared API-key mode and its configured authorization/entitlement checks.

OIDC cases, telemetry, access audit, playbooks, and control assessments are stored in separate SQLite databases per tenant. The filename uses a SHA-256 digest of the tenant claim, not the raw tenant identifier. Set `SANCTUM_TENANT_DATA_DIR` to a durable, access-restricted volume; protect backups and filesystem permissions. The existing single `SANCTUM_API_KEY` is disabled automatically when OIDC is configured. To temporarily retain legacy API-key authentication alongside OIDC, explicitly set `SANCTUM_ALLOW_LEGACY_API_KEY=true`; those legacy requests remain global and **are not tenant-isolated**, so do not enable this for a multi-tenant deployment without a controlled migration plan.

If source-authenticated telemetry push is enabled with OIDC, bind every source to exactly one tenant using `SANCTUM_EVENT_SOURCE_TENANTS` (JSON object mapping source ID to tenant ID). A source event is then stored in that tenant's telemetry database. File imports are stored under the authenticated user's tenant. Use distinct source credentials and tenant bindings; missing/invalid bindings fail closed.

The access audit records keyed HMAC pseudonyms of the verified OIDC subject and tenant in production, along with authentication method, route template, outcome, and a truncated credential fingerprint. In development, direct identity values can appear in local audit data. Request bodies, bearer tokens, query strings, and client IP addresses are not recorded. Audit metadata remains privacy-sensitive; apply access controls and retention. The SQLite audit is not tamper-proof or an immutable external audit service.

For the dashboard, enter the OIDC access token in the credential field prefixed with `Bearer `; the UI holds it in page memory only. Configure CORS to allow the dashboard origin and the `Authorization` header. The application does not implement an interactive OIDC login or token refresh flow; obtain the access token through your approved identity-provider client.

### Local event correlation and timelines

`POST /api/v1/events/correlate` accepts up to 1,000 caller-supplied events and requires the `X-API-Key` header. For example:

```json
{
  "events": [
    {
      "event_id": "evt-1",
      "event_type": "login",
      "correlation_key": "case-123",
      "source": "identity-provider",
      "observed_at": "2026-10-18T10:00:00Z",
      "severity": "MEDIUM"
    },
    {
      "event_id": "evt-2",
      "event_type": "privilege-change",
      "correlation_key": "case-123",
      "source": "identity-provider",
      "observed_at": "2026-10-18T10:02:00Z",
      "severity": "HIGH"
    }
  ]
}
```

Events sharing an exact `correlation_key` are returned in timestamp order with a SHA-256 key reference, source-reported priority, and reasons. Timestamps must include a timezone; severity must be one of `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, or `INFO`. Missing severity yields `NOT_ASSESSED`. The priority only summarizes caller-provided severity and is not a threat assessment; grouping does not establish malicious activity. Correlation through this endpoint is limited to one request. For persistent, normalized ingestion, use the separate telemetry endpoints below.

### Incident cases

Authenticated case endpoints persist triage records in SQLite at `~/.sanctum-suite/cases.sqlite3` by default. Set `SANCTUM_CASES_DB` to a durable, access-restricted path for deployments. Use `POST /api/v1/cases` to create a case; a correlated incident can be attached using its correlation ID, reported priority, reasons, and timeline. A correlation ID can be attached to only one case. Use `GET /api/v1/cases` (optional `status` and `limit` query parameters) to list cases and `GET /api/v1/cases/{case_id}` to read the timeline, notes, and evidence references.

`PATCH /api/v1/cases/{case_id}` updates `status` (`open`, `in_progress`, `resolved`, or `closed`) and/or `assigned_to`. Notes are appended with `POST /api/v1/cases/{case_id}/notes`. Evidence references (optionally with a SHA-256 digest) are appended with `POST /api/v1/cases/{case_id}/evidence`; evidence contents and uploaded files are not stored. The API-key holder supplies analyst names; these are operator-provided labels, not independently authenticated identities. Notes/references have no edit or delete endpoint in this version.

The dashboard workbench can create a case from a correlated incident, load cases, assign analysts, update status, add notes, and register evidence references. Set `NEXT_PUBLIC_SANCTUM_API_URL` in the dashboard environment. For cross-origin browser access, configure the API's `SANCTUM_CORS_ORIGINS` as an exact comma-separated list of dashboard origins, for example `http://localhost:3000`; wildcard origins are rejected. In legacy mode, enter the shared API key into the workbench; for OIDC, enter an access token prefixed with `Bearer `. Credentials are held in page memory only and are not persisted. Serve the dashboard and API over HTTPS in production, protect the dashboard against script injection, and do not distribute legacy shared API keys beyond trusted service operators.

### Simulated response playbooks

For an existing case, `POST /api/v1/cases/{case_id}/playbooks/simulate` with `{"simulated_by":"operator-label"}` creates a durable, recommendation-only plan snapshot from the case timeline, source-reported priority, and evidence-reference count. `GET /api/v1/cases/{case_id}/playbooks` lists its plans. A reviewer records an explicit decision using `POST /api/v1/playbooks/{plan_id}/decisions` with `decision` (`approve` or `reject`), `reviewer`, and a required `rationale`. Decisions are append-only and the latest decision sets the plan's review status.

Approval means **approved for manual review only**. It does not authorize or trigger response work. Plans contain human review and coordination steps only; no shell commands, external notifications, system changes, or containment actions are executed. The reported plan field remains `NOT_EXECUTED`. With OIDC, actor fields are populated from the validated token subject; in legacy API-key mode, supplied operator/reviewer labels remain caller-provided and are not independently authenticated identities. Keep separate organizational change-control and authorization processes.

### Privacy, access audit, and retention

Keep case text to the minimum needed for triage. Do not enter passwords, tokens, raw evidence, or unnecessary personal data into titles, summaries, notes, event fields, or evidence references. Evidence files are not uploaded. The access audit records the request method and route template, HTTP response code, timestamp, and a truncated credential fingerprint. For OIDC requests it also records the validated subject, tenant, and authentication method; for legacy API-key requests, the fingerprint identifies only the shared credential. It does not record request bodies, credentials, query strings, IP addresses, or the user-supplied analyst labels.

`GET /api/v1/governance/access-log` returns recent access records. `SANCTUM_CASE_RETENTION_DAYS` optionally deletes cases in `resolved` or `closed` status whose last update is older than the configured number of days. Deletion cascades to timeline entries, notes, evidence references, playbooks, and their decisions; open and in-progress cases are retained. `SANCTUM_ACCESS_AUDIT_RETENTION_DAYS` optionally deletes audit records older than the configured number of days. Both settings are unset by default (automatic deletion disabled) and accept values from 1 to 36500 days. Retention runs when an authenticated case, playbook, governance, event-correlation, or telemetry endpoint is called. `POST /api/v1/governance/retention/purge` applies the configured policies immediately and returns deletion counts. A `retention` audit entry records case purges; if audit retention is configured, old audit records including prior retention entries may also be deleted.

When OIDC is not configured, the API continues to use one shared `SANCTUM_API_KEY`; it does not provide per-user identity, roles, or tenant isolation. Its credential fingerprint identifies the shared key only. Request-provided reviewer/analyst names remain caller labels in legacy mode, not authenticated identities. Configure retention to meet approved organizational/legal requirements, protect backups to the same standard, and remember that SQLite/WAL backups may retain deleted data.

### Synthetic incident lab

The authenticated `GET /api/v1/lab/scenarios` endpoint lists fixed fictional scenarios. `POST /api/v1/lab/scenarios/{scenario_id}/run` generates a fresh in-memory event batch and returns its local correlation and timeline. The dashboard's **Synthetic incident lab** section can run these scenarios and add their visibly marked results to the workbench. A demo result may be explicitly saved as a case, but it is labeled as synthetic and follows the normal operator case workflow.

The lab uses synthetic event names, source labels, correlation keys, and timestamps only. It makes no external connections, does not read production telemetry, does not persist the generated events, and never executes response actions. Access to the lab endpoints is recorded in the access audit. Do not mix actual person, customer, asset, or incident data into a training scenario.

For preparing a separate, operator-managed Parrot OS virtual machine, use the non-executing [Parrot lab preflight](./PARROT_LAB.md). It verifies a local ISO against an operator-supplied digest and does not download, launch, or isolate a VM.

For PQC inventory review, offline-transfer manifests, eBPF implementation boundaries, and TEMPEST/SDIP-27 evidence limits, see [specialized security workflows](./SPECIALIZED_SECURITY.md).

### Preparing external telemetry ingestion

Telemetry ingestion is disabled until an operator configures both `SANCTUM_EVENT_SOURCE_KEYS` and `SANCTUM_EVENT_RETENTION_DAYS`. Store source secrets in the deployment secret manager, not in source control or dashboard configuration. `SANCTUM_EVENT_SOURCE_KEYS` is a JSON object mapping source IDs (1-64 ASCII letters, digits, `.`, `_`, or `-`) to separate secrets of at least 32 bytes. `SANCTUM_EVENT_RETENTION_DAYS` is required to ingest, has no default, and accepts 1-36500 days. `SANCTUM_EVENT_CORRELATION_WINDOW_HOURS` optionally limits correlation reads to events ingested in the last 1-720 hours (default 24). Retention and correlation lookback refer to ingestion time, not the source event timestamp.

`GET /api/v1/telemetry/connectors` (API key required) lists configured source IDs and available formats without exposing secrets. Server-to-server push uses `POST /api/v1/telemetry/ingest` with `X-Sanctum-Source-ID` and `X-Sanctum-Source-Key` headers, and a JSON body containing 1-1000 normalized events:

```json
{
  "events": [{
    "source_event_id": "source-local-id",
    "event_type": "identity.login",
    "observed_at": "2026-10-18T10:00:00Z",
    "severity": "MEDIUM",
    "correlation_token": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
  }]
}
```

File import uses `POST /api/v1/telemetry/import` with the normal `X-API-Key` and a JSON body containing `source_id`, `format` (`json`, `jsonl`, or `cef`), and `content` (up to 4 MB; up to 1000 events). Each imported source must also be configured in `SANCTUM_EVENT_SOURCE_KEYS`. JSON accepts an event array or `{"events":[...]}`; JSONL accepts one event object per nonblank line. CEF input requires a valid CEF header, numeric severity from 0 to 10, and an `rt` timestamp. For CEF correlation tokens, use `cs1Label=correlation_token cs1=<64-lowercase-hex-token>`. The Workbench reads the selected file into page memory for review and submission; the operator can clear the selection, and the content is cleared after each import attempt. It is not written to browser storage.

The shared normalized contract accepts source event ID, event type, timezone-aware timestamp, optional source-reported severity, an optional 64-character lowercase hexadecimal correlation token, and an optional detection scenario/rule ID pair. Unknown fields are rejected. Detection IDs are accepted as source-provided metadata; they do not prove that a test scenario ran or that an alert is genuine. Raw payloads are neither written to SQLite nor included in validation error responses. The store hashes source event IDs and correlation tokens, assigns internal UUIDs, and deduplicates by source plus hashed source event ID. This is pseudonymization, not anonymization: use an approved, stable pseudonymization scheme (preferably keyed and scoped to the organization) before sending any correlation token; do not send direct identifiers or unnecessary personal data. `GET /api/v1/telemetry/events` returns normalized records without those hashes. `POST /api/v1/telemetry/correlate` groups exact matching pseudonymous tokens among recently ingested records; this grouping is not a threat assessment and does not establish malicious activity.

For the bounded Purple Team replay flow, include `detection_scenario_id` and `detection_rule_id` together on normalized source events (JSON/JSONL import or push API). Correlate the events and save a correlation as a case. Then call `POST /api/v1/cases/{case_id}/purple-team/replays` with `scenario_id`, `expected_rule_id`, and `evaluated_by`. The replay compares the expected pair against detection IDs already stored in that case timeline and appends an immutable result record. It does not run an attack, initiate a detection, or connect to an EDR/XDR product. A no-match result means only that the exact pair was not present in the saved case timeline.

`GET /api/v1/cases/{case_id}/report` returns a JSON report with the case timeline, notes, evidence references, Purple Team replay records, limitations, and a SHA-256 digest of the canonical report JSON excluding the digest field itself. The digest is an integrity aid, not proof of authenticity, accuracy, completeness, or non-repudiation. Evidence contents are never included. The Workbench can download this JSON report after authentication.

Access to telemetry endpoints is recorded in the access audit using route templates and, for source credentials, the configured source ID. Request bodies, source secrets, source event IDs, correlation tokens, IP addresses, and query strings are not recorded. `SANCTUM_EVENT_RETENTION_DAYS` deletes old telemetry and associated expired batch metadata when an authenticated telemetry endpoint is called. The purge endpoint also applies telemetry retention and reports deleted-event counts.

Pull connectors are deliberately vendor-neutral extension points. No vendor connector, polling scheduler, network egress, or external source is enabled by default. An explicitly registered adapter can be invoked manually with the authenticated `POST /api/v1/telemetry/connectors/{source_id}/pull` endpoint. Its optional JSON body accepts a provider cursor and a batch limit from 1 to 1000:

```json
{"cursor": "provider-cursor", "limit": 100}
```

The source must be listed in `SANCTUM_EVENT_SOURCE_KEYS`, and event retention must be configured. The adapter must implement `PullEventSourceAdapter`, return no more than the requested number of normalized events, and use the returned `next_cursor` on the next request. The operator or an external scheduler is responsible for securely persisting that cursor; Sanctum does not retain pull checkpoints or retry failed requests. Adapter calls time out after 30 seconds, invalid adapter output is rejected, and only normalized allow-listed fields are persisted. Each adapter must be registered and deployed explicitly and operate under an operator-approved network, credential, retention, and error-handling policy. Do not point the service at production systems until those integrations and controls have been independently reviewed.

`sanctum serve` permits plain HTTP only on loopback by default. Binding to any other address requires both `SANCTUM_TLS_CERT_FILE` and `SANCTUM_TLS_KEY_FILE` to point to existing TLS files; Uvicorn then serves HTTPS directly. For a TLS-terminating proxy, set `SANCTUM_TRUST_TLS_TERMINATION_PROXY=true` only when network policy prevents direct access to the plaintext backend and allows ingress solely from that proxy.

Active audits and port/HTTPS checks also require an operator-configured exact target allowlist in `SANCTUM_AUTHORIZED_TARGETS`, a written authorization reference, and a valid signed entitlement. Configure `SANCTUM_LICENSE_PUBLIC_KEY` and `SANCTUM_LICENSE_KEY` in the deployment secret manager. With any of these unset, active audit execution is denied. See [COMMERCIAL_ENTITLEMENTS.md](./COMMERCIAL_ENTITLEMENTS.md) for token and scope details.

Example only, after the operator has approved the target and configured a signed license:

```powershell
$env:SANCTUM_AUTHORIZED_TARGETS = "app.example.test"
sanctum run-audit --target app.example.test --authorization-reference "change-approval-123"
sanctum scan-ports --host app.example.test --authorization-reference "change-approval-123"
```

The reference value is an operator audit trail pointer; it is not proof that authorization exists. The allowlist uses exact host matches and has no wildcard support. Do not run these commands against systems outside the approved scope.

For local Docker Compose evaluation, copy `.env.example` to `.env`, set a newly generated key, then run `Copy-Item .env.example .env
# Set SANCTUM_API_KEY in .env to a fresh value from:
# python -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose up --build`. The API port is bound to loopback by default. Do not bind it to a public interface until authentication, TLS termination, firewalling, request limits, and deployment-specific security controls have been reviewed.

## Install the dashboard

```powershell
Set-Location .\sanctum-dashboard
npm ci
Copy-Item .env.example .env.local
npm run build
npm run start
```

Set `NEXT_PUBLIC_SANCTUM_WS_URL` to the full WebSocket URL for the authorized API. Use `wss://` for deployments served over HTTPS.
The workbench WebSocket currently does not publish live telemetry and will close connections; the separately configured push/import endpoints do not automatically feed a WebSocket stream.
Copy `NEXT_PUBLIC_SANCTUM_API_URL` from `.env.example` into the dashboard environment to enable incident case operations; configure matching exact origins in the API's `SANCTUM_CORS_ORIGINS`.

For optional outbound delivery of completed-audit CEF events to an operator-approved HTTPS webhook, set `SANCTUM_SIEM_WEBHOOK_URL` and optionally `SANCTUM_SIEM_WEBHOOK_TOKEN` in the server secret manager. The token is sent as a Bearer credential; URL query strings, fragments, and embedded credentials are rejected. Delivery status is included in the audit report. No Sentinel, Splunk, Elastic, Wazuh, or other vendor-specific adapter is configured.

## Configure lead capture

The website's contact form forwards inquiries to an operator-managed webhook and does not store them in the dashboard application. Configure:

- `SANCTUM_LEAD_WEBHOOK_URL`: HTTPS URL for the approved lead intake integration
- `SANCTUM_LEAD_WEBHOOK_TOKEN`: optional bearer token, stored as a server-side secret

The webhook must accept a JSON POST containing `email`, `organization`, `message`, and `submittedAt`. Test successful, rejected, and unavailable webhook responses before publishing. Apply rate limiting, spam controls, access restriction, and an appropriate retention policy at the edge and provider.

The form remains unavailable until `SANCTUM_LEAD_WEBHOOK_URL` is configured. No webhook provider or endpoint has been selected in this deployment. Do not configure one until the processor, privacy terms, and retention policy are approved.

Do not place webhook credentials in `NEXT_PUBLIC_*` variables. Do not accept sensitive system or vulnerability details through the public lead form.

## Production release checks

1. Review the license and obtain written authorization for the intended use.
2. Run Python tests, dashboard linting, and a clean dashboard production build.
3. Configure TLS, secure secrets, access control, backups, logging, monitoring, and incident response.
4. Exercise every enabled feature in a test environment and review its permissions.
5. Confirm privacy disclosures, lead retention, support scope, and commercial contract terms.
6. Keep a rollback path and verify that no development credentials or test data are deployed.

This guide does not certify the application as production-safe. Operators remain responsible for validating their deployment and applicable legal obligations.

Several platform-specific modules are placeholders, not operational integrations. Container/SBOM and memory-forensics scanning, firmware analysis, GPU isolation, hardware enclaves, classified-data storage, autonomous red-team, multimodal/multi-turn model testing, EDR/XDR collection, satellite telemetry, covert channels, biometric coercion detection, hot-patching, and dead-man-switch actions are not performed unless a separately validated integration is supplied. The built-in envelope-encryption helper uses an ephemeral process-memory key unless Vault Transit is explicitly configured; production preflight requires Vault Transit.
