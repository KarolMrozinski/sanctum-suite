# Signed entitlements and authorized assessment scope

## Signed license tokens

SANCTUM-SUITE verifies compact offline entitlements signed with Ed25519. The token is two base64url segments separated by one dot:

```text
base64url(compact-json-claims).base64url(ed25519-signature-of-the-first-segment)
```

Required claims:

```json
{
  "license_id": "operator-issued-id",
  "tenant_id": "operator-issued-tenant",
  "tier": "COMMUNITY",
  "exp": 1792353600,
  "limits": {
    "max_audits_per_month": 5,
    "max_prompts_per_day": 50
  },
  "features": ["audit"]
}
```

The JSON and limits above are examples only, not approved prices or product tiers. No automated entitlement service, payment processor, or published commercial plan is configured. Keep the signing private key offline or in an operator-controlled signing service; the application receives only `SANCTUM_LICENSE_PUBLIC_KEY` and the signed `SANCTUM_LICENSE_KEY`. Do not commit either value. Unsigned prefix-based keys are rejected. Tokens expire according to their signed `exp` claim; online revocation is not implemented.

Usage counters are stored in SQLite at `SANCTUM_BILLING_DB` (default `~/.sanctum-suite/usage.sqlite3`) and incremented transactionally by tenant and UTC period. Back up and restrict this file. It is not a high-availability billing ledger.

## Manual sales-led issuance

The owner-selected model is manual, sales-led licensing without online checkout. An offline issuer command is available:

```powershell
sanctum issue-license `
  --private-key-file C:\secure\offline\sanctum-issuer-ed25519.pem `
  --license-id customer-contract-001 `
  --tenant-id customer-001 `
  --tier PROFESSIONAL `
  --expires-in-days 365 `
  --max-audits-per-month 100 `
  --max-prompts-per-day 1000 `
  --features audit,prompt-inspection
```

The command writes a JSON object containing the signed customer token and its corresponding public key. Keep the private key on an offline, access-restricted signing workstation; never copy it to the application service or send it to a customer. Configure the public key as `SANCTUM_LICENSE_PUBLIC_KEY` and deliver only the signed token through the approved sales channel. Issuance, delivery, renewal, cancellation, and revocation are not tracked by a central service. Choose limits and contract terms deliberately; this command does not enforce pricing or verify a customer contract.

## Active scanning scope

Active HTTPS and TCP checks require both:

- `SANCTUM_AUTHORIZED_TARGETS`: comma-separated exact hostnames or IP addresses configured by the operator; wildcards and subdomains are not implicitly included.
- A non-empty `authorization_reference` identifying written permission for the assessment.

The CLI requires `--target` and `--authorization-reference`. The API audit request requires `target_domain` and `authorization_reference`. The GitHub workflow also requires an exact target match against the operator-provided `SANCTUM_AUTHORIZED_TARGETS` secret. HTTP checks verify TLS and do not follow redirects. Configure network egress controls as defense in depth.

The reference string and operator allowlist do not independently prove legal authorization. The operator is responsible for recording and validating permission, scope, dates, rate limits, and emergency contacts before running active checks.

## Remaining commercial boundaries

This mechanism verifies and locally meters signed entitlements and can issue tokens manually from an offline signing workstation. It does not provide checkout, payment processing, customer sign-up, automated renewal, cancellation, revocation, account authentication, tenant-isolated control evidence, or a customer-facing billing portal. The current API key is service-wide, not tenant-bound. Do not offer isolated SaaS tenancy or claim payment integration until those controls are implemented and independently tested.
