<div align="center">

# SANCTUM SUITE

<p>
  <img src="https://img.shields.io/badge/Next.js-16.4.2-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js 16.4.2" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=white" alt="React 19" />
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript 5" />
  <img src="https://img.shields.io/badge/Tailwind-4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind CSS 4" />
  <img src="https://img.shields.io/badge/Node.js-20+-339933?style=for-the-badge&logo=node.js&logoColor=white" alt="Node.js" />
  <img src="https://img.shields.io/badge/C%23-9.0-239120?style=for-the-badge&logo=csharp&logoColor=white" alt="C#" />
  <img src="https://img.shields.io/badge/WPF-.NET-512BD4?style=for-the-badge&logo=.net&logoColor=white" alt="WPF" />
  <img src="https://img.shields.io/badge/PowerShell-7-5391FE?style=for-the-badge&logo=powershell&logoColor=white" alt="PowerShell" />
</p>

<p>
  <a href="http://localhost:3000"><img src="https://img.shields.io/badge/Launch%20Dashboard-Open-00E5FF?style=for-the-badge" alt="Launch Dashboard" /></a>
  <a href="INDEX.md"><img src="https://img.shields.io/badge/Repo%20Index-Open-7C3AED?style=for-the-badge" alt="Repo Index" /></a>
  <a href="docs/README.md"><img src="https://img.shields.io/badge/Docs-Open-94A3B8?style=for-the-badge" alt="Docs" /></a>
</p>

</div>

## Why Sanctum Suite exists

Sanctum Suite is a premium OpenCTI-inspired cyber threat intelligence workspace for analysts and security teams. It brings together a clean operational dashboard, a desktop-first launcher experience, and a product structure designed for demos, validation, and future real-world deployment.

## What it includes

- premium CTI dashboard for threats, entities, investigations, and alerts
- local-first desktop workflow for Windows use
- product-branded Sanctum Suite UI aligned to cyber-ops workflows
- modular repo structure ready for expansion and future integrations

## Quick start

### Run the dashboard locally

```bash
cd sanctum-dashboard
npm install
npm run dev
```

Open: `http://localhost:3000`

### Launch the desktop wrapper

From the repository root:

- `start-sanctum-suite.cmd`
- `run-sanctum-suite.bat`
- `sanctum-suite-gui-launcher.ps1`
- `SanctumSuiteLauncher.exe`

Sanctum Suite now stays quiet until you launch it intentionally; it no longer opens hidden background instances during startup.

### Clean stale background instances

If older Sanctum windows remain running in the background, use:

- `kill-stale-sanctum.ps1`
- `kill-stale-sanctum.cmd`

This helps clear stale local dashboard processes without a full reboot.

### Stop the runtime

```bash
stop-sanctum-suite.cmd
```

## Main product sections

- Overview
- Threats
- Entities
- Investigations
- Alerts

## Repository structure

```text
README.md        primary project overview
INDEX.md         repo index and navigation entrypoint
docs/            product docs, runbooks, release notes, and packaging guidance
desktop/         Windows launcher and installer-related assets
sanctum-dashboard/ app UI and CTI dashboard source
security/        security posture and governance docs
build/           packaging and deployment automation
```

## Documentation

- [INDEX.md](INDEX.md)
- [docs/README.md](docs/README.md)
- [docs/WINDOWS_INSTALLER.md](docs/WINDOWS_INSTALLER.md)
- [docs/PRODUCTION_PUBLICATION_RUNBOOK.md](docs/PRODUCTION_PUBLICATION_RUNBOOK.md)
- [SIGNING_POLICY.md](SIGNING_POLICY.md)
- [security/SECURITY.md](security/SECURITY.md)

## Release posture

The recommended production path for public Windows distribution is:

- EV code signing
- Azure Trusted Signing in CI/CD
- SHA-256 with timestamping
- MSI/WiX installer format

Advanced compliance modes such as WHQL, HLK, ELAM, PPL, MVI, FIPS 140-3, HSM, NIAPC/NATO, and NSA Type 1 remain supported as conditional enterprise or defense-aligned options, not as a blanket requirement for a standard CTI desktop application.

## Current status

The project is a polished local-first CTI prototype and product shell with a premium UI, desktop launcher workflow, and production-oriented release documentation. It is suitable for demos, validation, and expansion into a more complete live deployment model.

```yaml
# GitHub Actions / release environment secrets
WINDOWS_CERT_PFX_BASE64: "<base64-encoded-pfx-or-ev-certificate>"
WINDOWS_CERT_PASSWORD: "<certificate-password>"
WINDOWS_CERT_THUMBPRINT: "<thumbprint>"
AZURE_TENANT_ID: "<tenant-id>"
AZURE_CLIENT_ID: "<client-id>"
AZURE_CLIENT_SECRET: "<client-secret>"
AZURE_TRUSTED_SIGNING_ENDPOINT: "https://<region>.codesigning.azure.net"
AZURE_TRUSTED_SIGNING_ACCOUNT_NAME: "<account-name>"
AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME: "<profile-name>"
AZURE_TRUSTED_SIGNING_POLICY: "<optional-policy-name>"
ROOT_CA_CERT_PATH: "<optional-root-ca-path>"
ROOT_CA_CHAIN_PATH: "<optional-chain-path>"
MTLS_CLIENT_CERT_PATH: "<optional-client-cert-path>"
MTLS_CLIENT_CERT_PASSWORD: "<optional-client-cert-password>"
MTLS_CA_BUNDLE_PATH: "<optional-ca-bundle-path>"
BYO_PKI_CONFIG_PATH: "<optional-pki-config-path>"
FIPS1403_HSM_MODULE_PATH: "<optional-fips-module-path>"
FIPS1403_KEY_LABEL: "<optional-key-label>"
NIAPC_NATO_PKI_PROFILE: "<optional-profile>"
HSM_TOKEN: "<optional-hsm-token>"
HSM_KEY_ID: "<optional-key-id>"
NSA_TYPE1_KEYRING_PATH: "<optional-keyring>"
NSA_TYPE1_PROFILE: "<optional-profile>"
WHQL_SIGNING_CERT_THUMBPRINT: "<optional-whql-thumbprint>"
WHQL_SIGNING_CERT_PFX_BASE64: "<optional-whql-pfx-base64>"
HLK_CERT_THUMBPRINT: "<optional-hlk-thumbprint>"
HLK_CERT_PFX_BASE64: "<optional-hlk-pfx-base64>"
ELAM_SIGNING_CERT_THUMBPRINT: "<optional-elam-thumbprint>"
ELAM_SIGNING_CERT_PFX_BASE64: "<optional-elam-pfx-base64>"
PPL_SIGNING_CERT_THUMBPRINT: "<optional-ppl-thumbprint>"
PPL_SIGNING_CERT_PFX_BASE64: "<optional-ppl-pfx-base64>"
MVI_SIGNING_CERT_THUMBPRINT: "<optional-mvi-thumbprint>"
MVI_SIGNING_CERT_PFX_BASE64: "<optional-mvi-pfx-base64>"
```

GitHub variables:

```yaml
SIGNING_MODE: "auto" # or azure-trusted-signing / ev
REQUIRE_SIGNED_BUILD: "true"
PUBLISHER: "CN=Karol Mrozinski"
PRODUCT_NAME: "Sanctum Suite"
BUILD_VERSION: "1.0.0.0"
```

This is the final release hygiene template used before a public signed Windows installer is published.

## License

See [LICENSE](LICENSE).
