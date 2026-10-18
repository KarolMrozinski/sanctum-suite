# SANCTUM-SUITE 6.0.0 — Draft Release Notes

> Draft only. This release has not been published. Do not distribute for execution or commercial use unless the required written license authorization has been obtained.

## Highlights

- Python CLI and package distribution support.
- Dashboard product pages for About, Features, Documentation, Pricing, Privacy, and the operational Workbench.
- Lead inquiry form with server-side webhook integration point; it remains unavailable until configured.
- Installation, AWS deployment, security, and release documentation.
- Removed the sample incident stream and sample attack graph to avoid presenting fabricated data as live telemetry.
- API authentication now requires a unique `SANCTUM_API_KEY`; no built-in default credential is accepted.
- Docker Compose binds the API port to loopback and requires the deployment key.
- CI validates Python tests/build and the dashboard lint/build.
- Security audit workflow now requires a manually supplied target and explicit authorization confirmation.

## Known limitations

- Incident WebSocket telemetry is not connected to an authenticated event source.
- Lead webhook provider and endpoint are not configured.
- Privacy notice, legal/commercial terms, support SLA, payment processor, AWS account/region, and domain need owner/operator decisions and review.
- Pricing is not an active offer and payment/entitlement systems are not included.
- The repository license requires prior written permission for execution and commercial use.
- The existing billing/license manager is a development stub: tier prefixes are not cryptographically verified and usage counts are process-local. Do not use it as paid entitlement enforcement.

## Validation

Release CI should record exact Python/Node versions, test output, dashboard build, Python wheel/sdist, artifact checksums, and source revision before publication.
