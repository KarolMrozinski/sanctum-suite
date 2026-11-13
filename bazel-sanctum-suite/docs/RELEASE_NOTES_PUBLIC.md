# Sanctum Suite public release notes

## Release summary

Sanctum Suite is a premium OpenCTI-inspired cyber threat intelligence workspace designed for security analysts, responders, and teams that need a cleaner operational view of threat context, entity relationships, and investigations.

This release focuses on a polished CTI-style user experience, a clear desktop-first launcher flow, and a realistic Windows packaging and release posture for future production distribution.

## Highlights

- premium cyber-intelligence dashboard experience centered on threats, entities, investigations, and alerts
- role-focused analyst workflow and operational prioritization UX
- desktop launcher and Windows packaging preparation for a more native app feel
- formal API contract for future CTI backend integration
- production-ready installer and signing posture documentation for enterprise distribution
- GitHub Actions release pipeline structure aligned to signed Windows MSI packaging

## Key capabilities

- CTI dashboard with sections for overview, threats, entities, investigations, and alerts
- realistic analyst workflow for triage, investigation, and operational status review
- by-design local-first runtime with a path toward live backend data integration
- installation and signing guidance prepared for a customer-facing Windows release model
- repository-level release readiness documentation and security-policy alignment

## Signing and delivery model

For the production release path, Sanctum Suite follows the recommended enterprise-grade model:

- EV Code Signing for the public trust identity
- Azure Trusted Signing for secure cloud-managed signing in CI/CD
- SHA-256 signing and RFC3161 timestamping
- MSI/WiX as the native Windows installer format
- advanced compliance modes supported only when a governed environment requires them

This approach is intentionally more realistic and honest than claiming that every high-assurance or government-specific validation path is mandatory for a standard desktop CTI app.

## Supported future certification paths

The project is structured to support the following modes in principle for future enterprise or specialized deployment environments:

- X.509 certificate-based PKI
- mTLS / mutual TLS release authentication
- Root CA and BYO-PKI trust models
- FIPS 140-3 cryptographic compliance with HSM-backed material
- NIAPC / NATO-aligned secure PKI environments
- WHQL / HLK / ELAM / PPL / MVI where specifically required by compliant system scenarios
- additional specialized high-assurance modes such as NSA Type 1 or defense-grade PKI flows when the environment mandates them

These flows are documented as conditional and future-ready, not as default requirements for a standard CTI application.

## Production release requirement

A public, signed installation artifact must be generated from a Windows-hosted build/signing environment with valid credentials and must be verified before publication.

The repository contains the release pipeline, signing policy, and documentation needed to support the process, but the actual production signing and final validation still require a real certificate-backed Windows release environment.

## Known scope notes

- The app is a polished local-first CTI product shell with a realistic operational model.
- Live backend integration remains a downstream implementation step beyond the current contract and architecture layer.
- Certification and compliance modes are supported as future-ready paths, not as a blanket requirement for all users.
- The final public release should be executed only in a governed environment with valid Windows signing credentials.

## Recommended release posture

To maintain trust and operational clarity, the preferred public distribution path is:

1. build and validate on a clean Windows runner
2. sign with EV or Azure Trusted Signing
3. produce a signed MSI/WiX installer
4. verify installer integrity on a clean Windows target
5. publish only the verified signed artifact

## Final note

Sanctum Suite is positioned as a credible CTI workspace with a production-minded release story, while remaining honest about the distinction between a polished product shell and a fully deployed live backend environment.
