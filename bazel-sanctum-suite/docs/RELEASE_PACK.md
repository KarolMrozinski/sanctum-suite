# SANCTUM-SUITE — Release Overview

## Product summary

SANCTUM-SUITE is a source-available Python security engineering toolkit with a companion Next.js dashboard. Its modules cover audit orchestration, scanning, threat analysis, AI safety experiments, compliance support, analytics, reporting, and selected infrastructure integrations.

The project is intended for controlled evaluation by authorized security teams. Module maturity, platform support, permissions, and dependencies vary. Buyers should validate requirements and behavior before relying on any module.

## Intended audience

- Internal security engineering and SOC teams
- Organizations evaluating AI safety and security workflows
- Teams needing customizable audit/reporting utilities
- Integrators assessing a private deployment under a written license

## Deployment options

- **Local evaluation:** install the Python package in an isolated virtual environment.
- **Private dashboard:** build and run the Next.js dashboard in an operator-managed environment with a separately configured API.
- **Enterprise engagement:** agree scope, written execution rights, deployment model, support, and service levels before production use.

## Commercial options

Draft evaluation and team pricing is shown on the website for discussion only; it is not an active payment or subscription offer. Enterprise terms, support commitments, and license rights require a written agreement. No checkout or billing integration is included.

## Release contents

- Python package and CLI (`sanctum`)
- Next.js dashboard, including home, feature, documentation, pricing, privacy, and workbench routes
- Lead form integration using an operator-configured webhook
- Installation, security, release, and monetization documentation

## Release verification

The release process should record the tested Python and Node versions, dependency lock state, test results, build output, artifact hashes, source revision, and reviewer sign-off. Re-run all release checks from a clean checkout before publication.

## Important limitations

- A successful build or test suite is not a security certification or proof of production readiness.
- The contact form requires operator webhook configuration and provider-side privacy, rate-limit, and retention controls.
- The dashboard's workbench requires an API WebSocket endpoint; the marketing overview is not live telemetry.
- The repository license restricts execution and commercial use unless written authorization is obtained.
- No payment processing, entitlement enforcement, customer identity management, or SLA system is bundled.

## Contact and next steps

Review the repository's `LICENSE`, `SECURITY.md`, and `docs/INSTALLATION.md`. Before launch, finalize commercial terms, legal review, support ownership, privacy details, and deployment security responsibilities.
