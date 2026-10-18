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
