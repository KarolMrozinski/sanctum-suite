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

The API rejects protected requests and fails readiness unless `SANCTUM_API_KEY` is configured with at least 32 bytes. The SDK reads this variable by default; alternatively pass `api_key` explicitly. Do not store a production key in source control or a checked-in `.env` file.

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
The workbench endpoint currently does not publish live telemetry and will close WebSocket connections until a real authenticated event source is implemented.

The selected telemetry option is vendor-neutral CEF only. To send completed-audit CEF events to an operator-approved HTTPS webhook, set `SANCTUM_SIEM_WEBHOOK_URL` and optionally `SANCTUM_SIEM_WEBHOOK_TOKEN` in the server secret manager. The token is sent as a Bearer credential; URL query strings, fragments, and embedded credentials are rejected. Delivery status is included in the audit report. No Sentinel, Splunk, Elastic, Wazuh, or other vendor-specific adapter is configured.

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

Several platform-specific modules are placeholders, not operational integrations. Container/SBOM and memory-forensics scanning, firmware analysis, GPU isolation, hardware enclaves, classified-data storage, autonomous red-team, multimodal/multi-turn model testing, EDR/XDR collection, satellite telemetry, covert channels, biometric coercion detection, hot-patching, and dead-man-switch actions are not performed unless a separately validated integration is supplied. The built-in envelope-encryption helper uses an ephemeral process-memory key; do not use it as a production KMS or for durable customer secrets.
