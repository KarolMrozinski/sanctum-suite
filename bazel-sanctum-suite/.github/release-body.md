# Sanctum Suite v1.0.0 - public signed Windows installer

## Release summary

Sanctum Suite is a premium OpenCTI-inspired cyber threat intelligence workspace for analysts and security teams.

This release ships the signed Windows MSI installer for the Sanctum Suite desktop experience, including the CTI dashboard, analyst workflow surfaces, and the Windows deployment-ready packaging model.

## Highlights

- premium CTI dashboard experience centered on threats, entities, investigations, and alerts
- desktop-first launch flow and installer-compatible packaging model
- OpenCTI-inspired analyst workflow with a product-branded Sanctum Suite identity
- real-data-ready architecture and API contract for future backend integration
- production-oriented signing and release posture for Windows distribution

## Signing and trust model

This installer is released under the recommended production posture:

- EV Code Signing for public trust
- Azure Trusted Signing in CI/CD for secure cloud-based signing
- SHA-256 signing with timestamping
- MSI/WiX as the primary Windows installer format

## Included artifacts

- `SanctumSuite-1.0.0.msi`
- `sha256sum.txt`
- installer verification summary

## Installation instructions

1. Download the signed MSI.
2. Run the installer on a supported Windows machine.
3. Accept the installation prompts.
4. Launch Sanctum Suite from the Start menu or desktop shortcut.
5. Confirm the app starts correctly and the dashboard loads the default CTI workspace.

## Verification

Before use in production, validate the installer on a clean Windows target and confirm:

- the certificate chain is valid
- the installer signature is present
- the MSI installs without warnings that affect trust or integrity
- the app launches normally after installation
- uninstall/repair flows behave as expected

## Notes

This release is intended for authenticated, controlled Windows distribution in a governed environment. The project supports advanced enterprise and compliance pathways for future deployment scenarios, but the public default release posture remains EV + Azure Trusted Signing with signed MSI delivery.

## Release checklist

- [x] signed installer verified on Windows
- [x] certificate chain accepted by the verifier
- [x] install test passed
- [x] startup validation passed
- [x] artifact hash or manifest reviewed
- [x] release tags and notes published
