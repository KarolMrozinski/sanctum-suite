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

Sanctum Suite was created to give security teams a sharper, more focused way to work with threat intelligence, operational context, and investigation flow. It brings together a premium analyst interface, local-first access, and desktop-like execution into one cohesive workspace designed to reduce noise and help teams move faster when investigating risk.

## Product overview

Sanctum Suite is structured as a high-end local-first CTI environment with a clear operational flow across intelligence, investigation, and response-oriented views. It combines the visual language of a modern security operations console with practical UX patterns suited for demos, internal review, and future deployment to an external environment.

### What’s inside

- OpenCTI-inspired analyst dashboard with threat intelligence workflow
- Structured views for overview, threats, entities, investigations, and alerts
- Premium dark-glass UI with crisp hierarchy and active monitoring cues
- Local-first runtime with desktop launcher flow for Windows users
- Modular repo layout prepared for future integrations and real data sources

### Core capabilities

- Threat-centric intelligence overview
- Entity relationship and context views
- Investigation tracking and analyst workflow support
- Alert monitoring and live-style operational summaries
- Desktop launch shell with URL-aware runtime targeting
- Clean product architecture and documentation-first repo organization

### Why teams use it

Sanctum Suite is designed to help security teams move from signal to decision without losing context. It presents the operational picture in a cleaner, more actionable way: suspicious activity is grouped, related entities are surfaced, and investigations can be followed with less friction.

## How it works

```text
Collect telemetry -> correlate entities and indicators -> prioritize investigations -> contain and track response
```

This flow keeps the platform grounded in a realistic security workflow while preserving the premium product feel of the interface.

## Product story and value

Sanctum Suite exists to make cyber operations feel more focused and more decisive. Whether the task is monitoring a suspicious domain, following a phishing cluster, or reviewing active investigations, the product gives operators one place to understand the signal and respond with confidence.

## Quick start

### 1. Run the dashboard locally

```bash
cd sanctum-dashboard
npm install
npm run dev
```

Then open:

- `http://localhost:3000`

### 2. Launch the desktop wrapper

From the repository root, use one of the supported entrypoints:

- `start-sanctum-suite.cmd`
- `run-sanctum-suite.bat`
- `sanctum-suite-gui-launcher.ps1`
- `SanctumSuiteLauncher.exe`

### 3. Stop or reset the runtime

```bash
stop-sanctum-suite.cmd
```

This keeps the lifecycle clean and prevents duplicate process or browser reopen loops.

### 4. Explore the main product sections

- Overview
- Threats
- Entities
- Investigations
- Alerts

## Product preview

<div align="center">

<img src="https://img.shields.io/badge/Threat%20Intel-Operational-00E5FF?style=for-the-badge" alt="Threat Intel" />
<img src="https://img.shields.io/badge/Entity%20Graph-Live-7C3AED?style=for-the-badge" alt="Entity Graph" />
<img src="https://img.shields.io/badge/Investigation%20Flow-Ready-22C55E?style=for-the-badge" alt="Investigation Flow" />

</div>

This product experience is intentionally tuned to feel like a live security command surface rather than a generic starter app.

## Root-level naming standard

The repository is organized around a clean product-first naming model:

```text
README.md          primary product landing page
INDEX.md           repository overview and navigation entrypoint
docs/              documentation and operational references
app/               application layer and system runtime logic
desktop/           desktop shell and native launcher package
integrations/      integration references and external system hooks
security/          security posture, guidance, and hardening docs
resources/         brand assets, visuals, and supporting resources
build/             packaging and release-oriented build artifacts
reports/           operational summaries and report exports
```

Legacy support files remain available for compatibility, while the structure above represents the final product-facing standard.

## Repository layout

```text
app/           Product runtime and application logic
desktop/       Desktop launcher and Windows app wrapper
integrations/  External integrations, references, and system hooks
security/      Security documentation and governance
resources/     Brand assets and design resources
docs/          Documentation, runbooks, and product notes
build/         Packaging, build, and deployment scaffolding
reports/       Generated reports and operational exports
```

## Technology stack

| Layer | Stack |
|---|---|
| Frontend | Next.js + React + TypeScript |
| Styling | Tailwind CSS + glassmorphism + cyber UI |
| Runtime | Node.js + npm + local development server |
| Desktop wrapper | .NET + C# + WPF + Windows launcher flow |
| Automation | PowerShell + CMD + BAT startup scripts |
| Security model | Python + Rust + future security tooling layers |

## Documentation and navigation

- [INDEX.md](INDEX.md)
- [sanctum-dashboard/README.md](sanctum-dashboard/README.md)
- [docs/README.md](docs/README.md)
- [security/SECURITY.md](security/SECURITY.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [CHANGELOG.md](CHANGELOG.md)
- [LICENSE](LICENSE)

## Design language

Sanctum Suite follows a premium cyber-operations visual system built around:

- deep navy and graphite surfaces
- cyan and teal signal accents
- glass-effect panels with soft glow
- dense, analyst-first workspace layout
- minimal premium chrome for a desktop-native feel

## Current status

The project currently sits in a polished local-first operational prototype phase: the CTI interface is fully styled and functional, the desktop launcher layer is substantially improved, and the repo is organized around a more product-ready structure. It is ready for local demos, validation, and future expansion into external deployment or live backend integration.

## Production release posture

Sanctum Suite is positioned as a premium CTI workspace with a realistic Windows release pipeline. The default and most credible production model is:

- EV Code Signing for the public trust identity
- Azure Trusted Signing in CI/CD for secure cloud-managed signing
- SHA-256 signing with valid timestamping
- MSI/WiX as the native Windows installer format
- optional future compliance or Microsoft validation paths only when the product architecture genuinely requires them

This is intentionally more honest and production-ready than claiming that WHQL, HLK, ELAM, PPL, MVI, NIAPC/NATO, FIPS 140-3, HSM Class 4, or NSA Type 1 are generic requirements for a standard desktop CTI app. The repository supports those modes for future enterprise or defense-aligned scenarios, but they remain conditional when the product is not operating in a specialized compliance environment.

## Required release secrets and variables

The signed release pipeline expects the following GitHub configuration before a final public installer is published.

### Recommended production secrets

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

### Advanced or compliance-mode secrets

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

### Required GitHub variables

- `SIGNING_MODE` = `auto` or `azure-trusted-signing`
- `REQUIRE_SIGNED_BUILD` = `true`
- `PUBLISHER` = `CN=Karol Mrozinski`
- `PRODUCT_NAME` = `Sanctum Suite`

### Final release checklist

- [ ] Windows runner and WiX Toolset available
- [ ] Node.js 22 and .NET 10 toolchain installed in the pipeline
- [ ] production dashboard build passes
- [ ] desktop launcher publish succeeds
- [ ] MSI generated successfully
- [ ] signing secret set is present and valid
- [ ] release artifact is signed before publication
- [ ] installer tested on a clean Windows environment
- [ ] final release notes document the signing model and certificate chain

## GitHub Actions secrets template

Use the following template in GitHub repository or environment settings before publishing a signed public release.

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
