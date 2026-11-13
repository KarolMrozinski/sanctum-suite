Sanctum Suite v1.0.0

Sanctum Suite is a premium OpenCTI-inspired cyber threat intelligence workspace designed for analysts and security teams who need a sharper, more structured way to move from signal to action.

This release delivers the signed Windows MSI installer for the Sanctum Suite desktop experience, including the CTI dashboard, operational security sections, and a Windows-ready release package.

Highlights

- Premium CTI dashboard experience centered on threats, entities, investigations, and alerts
- Desktop-first installation and startup flow
- OpenCTI-inspired analyst experience with Sanctum Suite branding and product identity
- Real-data-ready API contract and architecture for future backend integration
- Production-oriented Windows packaging and release posture
- Recommended public release model using EV code signing and Azure Trusted Signing

Included artifacts

- SanctumSuite-1.0.0.msi
- sha256sum.txt
- signed installer verification metadata
- release notes and validation summary

Installation

1. Download the signed MSI from this release.
2. Run the installer on a supported Windows machine.
3. Accept the installation prompts.
4. Launch Sanctum Suite from the desktop shortcut or Start menu.
5. Confirm the application opens and the CTI dashboard loads correctly.

Signing and trust model

This installer follows the recommended production release posture:

- EV Code Signing
- Azure Trusted Signing in CI/CD
- SHA-256 signing with timestamping
- MSI/WiX as the primary Windows installer format

This is the recommended public distribution model for Windows deployment.

Verification requirements

Before treating this build as production-ready, validate on a clean Windows target and confirm:

- the certificate chain is valid
- the installer signature is present
- the MSI installs without trust or integrity warnings
- the app launches correctly
- the primary CTI dashboard sections render without major issues
- uninstall and repair flows behave correctly
- hash or checksum validation matches the published file

Notes

This release is intended for controlled, trusted Windows distribution in a governed production environment. The project supports advanced enterprise and compliance pathways for future deployment scenarios, but the default public release posture remains EV + Azure Trusted Signing with signed MSI delivery.

Release checklist

- signed installer verified on Windows
- certificate chain accepted by the verifier
- installer installs successfully
- application launches successfully
- release hash or manifest reviewed
- release tag v1.0.0 published
- GitHub release notes published
