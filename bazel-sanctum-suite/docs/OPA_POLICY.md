# OPA API authorization

The API integrates with an operator-managed Open Policy Agent (OPA) service.
SANCTUM-SUITE does not start or administer OPA, distribute policy bundles, or
provide a policy decision point when the configured service is unavailable.

## Configure the decision endpoint

Set these server-side values in the deployment secret manager:

```powershell
$env:SANCTUM_OPA_URL = "https://opa.internal.example"
$env:SANCTUM_OPA_BEARER_TOKEN_FILE = "C:\secure\opa-token"
$env:SANCTUM_OPA_CA_CERT = "C:\secure\opa-ca.pem"
```

The token file and custom CA are optional when the trusted OPA endpoint does not
require them or uses a CA in the system trust store. Mount secret files
read-only. The API calls:

```text
POST /v1/data/sanctum/api/authz/decision
```

The OPA input contains only:

```json
{
  "identity": {
    "authentication_method": "oidc",
    "tenant_id": "tenant-a",
    "roles": ["AUDITOR"]
  },
  "request": {
    "method": "POST",
    "route": "/api/v1/cases"
  }
}
```

Every protected `/api/v1` route evaluates policy before executing, including
source-key-authenticated telemetry ingestion.

The matched route is a FastAPI route template; concrete path values, request
bodies, query parameters, headers, credentials, and subject identifiers are not
sent. Tenant-scoped storage and the existing local role checks remain in force.
Do not place personal data or secrets in policy decision logs.

## Decision contract and failure behavior

The policy decision endpoint must return HTTP 200 with a result matching:

```json
{
  "result": {
    "allow": true,
    "policy_version": "1.0.0"
  }
}
```

`allow` must be a JSON boolean and `policy_version` a non-empty version token.
Responses are limited to 16 KiB. Redirects, non-200 responses, malformed
documents, missing policy versions, oversized responses, and network failures
fail closed with HTTP 503. A valid `allow: false` decision returns HTTP 403.
Decisions and policy versions are retained in the existing API access audit.

In production and air-gapped profiles, `SANCTUM_OPA_URL` is required and
readiness checks that OPA evaluates a canary input as denied. Development
environments may omit OPA and use the existing local RBAC checks; once an OPA
URL is configured there is no RBAC fallback on service failure.

## Starter policy behavior

Load [authz.rego](../policies/sanctum/api/authz.rego) as package
`sanctum.api.authz`. It preserves the existing authorization boundary:

- A legacy shared API key retains its prior access, including to the legacy
  audit and analytics routes.
- OIDC identities cannot use `/api/v1/audit` or `/api/v1/analytics`, because
  those stores are not tenant-scoped.
- Authenticated OIDC users may read the protected API routes.
- `ADMIN` may perform tenant-scoped writes.
- `AUDITOR` may write cases, controls, playbooks, and the retention-purge
  operation. `VIEWER` is read-only.
- A configured telemetry event-source credential may only call
  `POST /api/v1/telemetry/ingest`.
- Existing local OIDC authorization runs after OPA and can still deny access.

Every policy change must update `policy_version`, be tested in the OPA
deployment pipeline, and be reviewed before rollout. The version is recorded
with each API access decision and returned by a successful production readiness
response. The API does not certify the completeness or correctness of
operator-supplied policies.
