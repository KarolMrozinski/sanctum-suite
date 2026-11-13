# Sanctum Suite — Repository Index

<div align="center">

# SANCTUM SUITE

<p>
  <a href="README.md"><img src="https://img.shields.io/badge/Main%20Repo-Open-00E5FF?style=for-the-badge" alt="Main Repo" /></a>
  <a href="sanctum-dashboard/README.md"><img src="https://img.shields.io/badge/Dashboard-Open-7C3AED?style=for-the-badge" alt="Dashboard" /></a>
  <a href="docs/README.md"><img src="https://img.shields.io/badge/Docs-Open-94A3B8?style=for-the-badge" alt="Docs" /></a>
</p>

</div>

## Overview

Sanctum Suite is a premium cyber threat-intelligence workspace built around a dark OpenCTI-inspired analyst experience and rebranded into the Sanctum Suite identity. The repo combines a live-like dashboard, operational CTI sections, desktop-style launch flow, and modular infrastructure for future real-world deployment.

## Repository map

```text
app/                 Product application and runtime logic
desktop/             Desktop shell and Windows launcher resources
integrations/        External references, connectors, and integration layers
security/            Security documentation, audits, policy references
resources/           Brand assets, icons, visual resources, and support files
docs/                Documentation, notes, notebooks, and repo guidance
build/               Build, packaging, and release-oriented utilities
reports/             Generated reports, outputs, and audit summaries
```

## Key project areas

### Application layer
- [app](app)
- [sanctum-dashboard](sanctum-dashboard)
- [sanctum-dashboard/README.md](sanctum-dashboard/README.md)

### Desktop launcher layer
- [desktop](desktop)
- [start-sanctum-suite.cmd](start-sanctum-suite.cmd)
- [stop-sanctum-suite.cmd](stop-sanctum-suite.cmd)
- [run-sanctum-suite.bat](run-sanctum-suite.bat)
- [sanctum-suite-gui-launcher.ps1](sanctum-suite-gui-launcher.ps1)

### Integration and security layer
- [integrations](integrations)
- [security](security)
- [security/SECURITY.md](security/SECURITY.md)

### Documentation and resources
- [docs](docs)
- [resources](resources)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [CHANGELOG.md](CHANGELOG.md)
- [LICENSE](LICENSE)

## Product focus

- Threat intelligence workspace
- Analyst-first dashboard UX
- Live-like data sections: Overview, Threats, Entities, Investigations, Alerts
- Desktop-mode startup and single-instance behavior
- Local-first workflow with future external URL readiness

## Local run

```bash
cd sanctum-dashboard
npm install
npm run dev
```

Open:

- `http://localhost:3000`

## Documentation

- [README.md](README.md)
- [docs/README.md](docs/README.md)
- [security/SECURITY.md](security/SECURITY.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [notebooks/sanctum_deep_dive.ipynb](notebooks/sanctum_deep_dive.ipynb)

## Production release and signing model

Sanctum Suite is organized around a premium CTI product identity and a realistic Windows release story. The project supports a production-ready public release path based on:

- EV Code Signing for public trust and customer-facing distribution
- Azure Trusted Signing in GitHub Actions for secure cloud-based code signing
- MSI/WiX as the delivery format for Windows installation
- optional enterprise or government compliance modes only when those environments are genuinely required

This model is intentionally aligned with the real-world release posture for a desktop CTI application and avoids over-claiming WHQL/HLK/ELAM/PPL/MVI/NIAPC/NATO/FIPS/HSM/NSA Type 1 requirements unless the architecture or deployment environment demands them.

## Required GitHub configuration for release

For production signing, configure the repository and environment settings with the following secrets and variables.

### Recommended secrets

- `WINDOWS_CERT_PFX_BASE64`
- `WINDOWS_CERT_PASSWORD`
- `WINDOWS_CERT_THUMBPRINT`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TRUSTED_SIGNING_ENDPOINT`
- `AZURE_TRUSTED_SIGNING_ACCOUNT_NAME`
- `AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME`
- `AZURE_TRUSTED_SIGNING_POLICY` (optional)

### Advanced environment-specific secrets

- `ROOT_CA_CERT_PATH`
- `ROOT_CA_CHAIN_PATH`
- `MTLS_CLIENT_CERT_PATH`
- `MTLS_CLIENT_CERT_PASSWORD`
- `MTLS_CA_BUNDLE_PATH`
- `BYO_PKI_CONFIG_PATH`
- `FIPS1403_HSM_MODULE_PATH`
- `FIPS1403_KEY_LABEL`
- `NIAPC_NATO_PKI_PROFILE`
- `HSM_TOKEN`
- `HSM_KEY_ID`
- `NSA_TYPE1_KEYRING_PATH`
- `NSA_TYPE1_PROFILE`
- `WHQL_SIGNING_CERT_THUMBPRINT`
- `WHQL_SIGNING_CERT_PFX_BASE64`
- `HLK_CERT_THUMBPRINT`
- `HLK_CERT_PFX_BASE64`
- `ELAM_SIGNING_CERT_THUMBPRINT`
- `ELAM_SIGNING_CERT_PFX_BASE64`
- `PPL_SIGNING_CERT_THUMBPRINT`
- `PPL_SIGNING_CERT_PFX_BASE64`
- `MVI_SIGNING_CERT_THUMBPRINT`
- `MVI_SIGNING_CERT_PFX_BASE64`

### Required variables

- `SIGNING_MODE` = `auto` or `azure-trusted-signing`
- `REQUIRE_SIGNED_BUILD` = `true`
- `PUBLISHER` = `CN=Karol Mrozinski`
- `PRODUCT_NAME` = `Sanctum Suite`

## Final release readiness checklist

- [ ] GitHub secrets are populated for the selected signing mode
- [ ] Windows build agent and WiX Toolset are available
- [ ] build pipeline completes successfully in CI
- [ ] installer artifact is generated and signed
- [ ] signed MSI is validated on a clean Windows system
- [ ] release artifact is published only after verification
- [ ] compliance-specific settings are enabled only for environments that require them

## Documentation trail

- [docs/RELEASE_READINESS_CHECKLIST.md](docs/RELEASE_READINESS_CHECKLIST.md)
- [docs/RELEASE_NOTES_PUBLIC.md](docs/RELEASE_NOTES_PUBLIC.md)
- [docs/WINDOWS_INSTALLER.md](docs/WINDOWS_INSTALLER.md)
- [SIGNING_POLICY.md](SIGNING_POLICY.md)

## Notes

This root index is the entry point for the repository and reflects the premium structure of the project without removing legacy compatibility files.
