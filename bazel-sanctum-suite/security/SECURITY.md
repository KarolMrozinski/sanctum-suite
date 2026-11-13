# Security Policy

## Supported versions

The project currently supports the latest release branch and the latest pre-release branch used for validation.

## Reporting a vulnerability

Please report security issues privately and responsibly.

1. Send details to the maintainer via a private channel or GitHub Security Advisory.
2. Include:
   - affected component or package
   - reproduction steps
   - impact assessment
   - suggested remediation, if available
3. Allow a reasonable response window for triage, verification, and coordinated disclosure.

Do not open public issues for vulnerabilities before a fix is ready.

## Disclosure expectations

- We aim to acknowledge reports within 5 business days.
- We will provide a remediation plan or status update as soon as a fix path is confirmed.
- We may ask for additional evidence or environment details required to validate the report.

## Security posture

This project is intended for security, defense, and enterprise resilience workflows. Production use must include:

- isolated deployment environments
- strong secret management
- least-privilege access controls
- network segmentation for API and dashboard surfaces
- monitoring, logging, and alerting for runtime integrity

## Release readiness

The project is considered production-ready for controlled deployment and commercial evaluation only when:

- package installation succeeds
- test suite passes
- CLI commands run without encoding or terminal failures
- security reporting flow is documented
- deployment environment and secrets model are reviewed by the operator

This repository does not currently establish production readiness, compliance, certification, or multi-tenant isolation. Active HTTPS/TCP checks require an exact host in `SANCTUM_AUTHORIZED_TARGETS`, a written authorization reference, and a valid signed entitlement. Do not use wildcard scopes or run tests outside written authorization. Network egress controls are required as defense in depth.
