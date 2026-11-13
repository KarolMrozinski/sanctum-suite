# Windows installer build and signing

This repository includes a Windows release pipeline for Sanctum Suite built around a native MSI/WiX package, with a compatible path toward EV code signing and Azure Trusted Signing. The installer packages the published .NET launcher together with the embedded dashboard runtime.

## Recommended signing model

For a production-grade Windows distribution, the strongest practical stack is:

- EV Code Signing certificate for the final release identity and trust chain
- Azure Trusted Signing for secure key custody, certificate lifecycle, and cloud-based signing workflows
- WHQL / HLK validation where the app is intended to be driver-like or kernel-adjacent or loaded in enterprise-managed device scenarios
- ELAM / PPL hardening for sensitive kernel or system-integration scenarios when the product is used in security-sensitive endpoints
- MVI / Microsoft validation programs only when the product is explicitly a Windows security, endpoint-protection, or system-integration component and the program applies

For a normal desktop CTI app, the realistic and recommended combination is:

1. EV code signing certificate for the release identity
2. Azure Trusted Signing as the operational signing service
3. SHA-256 signing + RFC3161 timestamping
4. optional WHQL/HLK only if the software includes kernel components, drivers, or enterprise endpoint integration that requires Microsoft hardware/driver validation
5. ELAM/PPL only when you are building a system-level protection component, not a general desktop app
6. MVI only when the product is a certified Microsoft security program participant

This repository intentionally supports all of these certification paths in a future-ready way, while keeping the default build path honest and practical for a standard CTI desktop app.

## Requirements

- Windows 11 or Windows Server 2022+ build agent
- WiX Toolset installed
- Windows 10/11 SDK (`signtool.exe`, `makeappx.exe` when used for MSIX)
- .NET 10 SDK
- Node.js 22 and dashboard dependencies
- A production signing method: either a `.pfx` certificate or Azure Trusted Signing credentials

## Required GitHub secrets and variables

Before a production release is considered valid, configure both repository secrets and variables in GitHub.

### Required secrets for the standard public release path

These are the minimal production credentials for the recommended EV + Azure Trusted Signing model:

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

### Required secrets for enterprise PKI and advanced signing modes

These are optional, but become required when the release is executed under a specific enterprise or high-assurance posture:

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

### Required variables for CI/CD release behavior

Set these as repository or environment variables:

- `SIGNING_MODE` = `auto` or `azure-trusted-signing` for production releases
- `REQUIRE_SIGNED_BUILD` = `true` for public production artifacts
- `BUILD_VERSION` or release tag version used by the package pipeline
- `PUBLISHER` = `CN=Karol Mrozinski`
- `PRODUCT_NAME` = `Sanctum Suite`

### Production signing decision matrix

| Release type | Preferred mode | Required secret set |
|---|---|---|
| Public enterprise release | `azure-trusted-signing` or `ev` | `AZURE_*` and/or `WINDOWS_CERT_*` |
| Private enterprise PKI | `x509`, `root-ca`, `byo-pki`, `mtls` | enterprise PKI variables |
| FIPS/HSM environment | `fips1403`, `hsm-fips1403-class4` | `FIPS1403_*`, `HSM_*` |
| Government or defense environment | `niapc-nato`, `nsa-type-1` | accredited PKI / keyring profile variables |
| Microsoft validation program | `whql`, `hlk`, `elam`, `ppl`, `mvi` | specific Microsoft validation certificate secrets |

The build script signs the generated MSI with either:

- a local PFX certificate via `signtool` and SHA-256 timestamping, or
- Azure Trusted Signing via the Azure CLI `az trusted-signing code-sign` command, or
- a prepared enterprise / compliance-mode flow that requires project-specific credentials and secure infrastructure

## Final production readiness checklist for signed MSI

Use the checklist below before publishing a signed Windows release.

### Build environment checklist

- [ ] Windows-hosted build agent or equivalent Windows signing environment available
- [ ] WiX Toolset installed and detected by the build pipeline
- [ ] .NET 10 SDK available
- [ ] Node.js 22 available and `npm ci` succeeds in `sanctum-dashboard`
- [ ] `npm run build` completes successfully
- [ ] desktop launcher publish succeeds with `.NET publish`
- [ ] MSI is generated successfully in `release/installer`

### Signing checklist

- [ ] `SIGNING_MODE` selected correctly for the target environment
- [ ] `REQUIRE_SIGNED_BUILD=true` set for final public release
- [ ] EV certificate or Azure Trusted Signing credentials are present
- [ ] `signtool.exe` is available when a local certificate flow is used
- [ ] timestamping service is reachable and valid
- [ ] signing store or key material is not exposed in repo files or logs
- [ ] certificate chain and trust path validated before release

### Security and compliance checklist

- [ ] private keys are stored in a secure secret store or HSM-backed environment
- [ ] no private key material is committed to the repository
- [ ] release artifacts have hash/manifest validation enabled
- [ ] release pipeline publishes only signed artifacts for final distribution
- [ ] optional compliance profiles (WHQL / HLK / ELAM / PPL / MVI / NSA Type 1 / NIAPC-NATO / FIPS 140-3) are used only when the product truly requires them

### Release checklist

- [ ] GitHub release tag created
- [ ] `release-installer.yml` workflow ran successfully on Windows runner
- [ ] `*.msi` artifact uploaded and verified
- [ ] artifact signature validated on a clean Windows machine
- [ ] install/uninstall flow tested in a clean VM or fresh OS image
- [ ] final release notes mention the signing model and trust chain used

## Release secrets section

Use the following section in GitHub Actions, repository settings, or a final release checklist when preparing a public licensed installer build.

```yaml
# GitHub repository secrets
WINDOWS_CERT_PFX_BASE64: "<base64-encoded-pfx-or-ev_certificate>"
WINDOWS_CERT_PASSWORD: "<certificate-password>"
WINDOWS_CERT_THUMBPRINT: "<certificate-thumbprint>"
AZURE_TENANT_ID: "<azure-tenant-id>"
AZURE_CLIENT_ID: "<azure-client-id>"
AZURE_CLIENT_SECRET: "<azure-client-secret>"
AZURE_TRUSTED_SIGNING_ENDPOINT: "https://<region>.codesigning.azure.net"
AZURE_TRUSTED_SIGNING_ACCOUNT_NAME: "<trusted-signing-account>"
AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME: "<certificate-profile-name>"
AZURE_TRUSTED_SIGNING_POLICY: "<optional-policy-name>"
ROOT_CA_CERT_PATH: "<optional-root-ca-path>"
ROOT_CA_CHAIN_PATH: "<optional-ca-chain-path>"
MTLS_CLIENT_CERT_PATH: "<optional-mtls-client-cert-path>"
MTLS_CLIENT_CERT_PASSWORD: "<optional-mtls-client-cert-password>"
MTLS_CA_BUNDLE_PATH: "<optional-ca-bundle-path>"
BYO_PKI_CONFIG_PATH: "<optional-pki-config>"
FIPS1403_HSM_MODULE_PATH: "<optional-fips-module>"
FIPS1403_KEY_LABEL: "<optional-key-label>"
NIAPC_NATO_PKI_PROFILE: "<optional-profile>"
HSM_TOKEN: "<optional-hsm-token>"
HSM_KEY_ID: "<optional-hsm-key-id>"
NSA_TYPE1_KEYRING_PATH: "<optional-keyring-path>"
NSA_TYPE1_PROFILE: "<optional-nsa-profile>"
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

```yaml
# GitHub repository variables
SIGNING_MODE: "auto" # or ev / azure-trusted-signing
REQUIRE_SIGNED_BUILD: "true"
BUILD_VERSION: "1.0.0.0"
PUBLISHER: "CN=Karol Mrozinski"
PRODUCT_NAME: "Sanctum Suite"
```

This section is the final release-secret template for the production pipeline. Only populate the required values for the selected signing mode.

## Local build

From a Windows PowerShell shell:

```powershell
cd C:\path\to\sanctum-suite
./desktop/installer/build-msi.ps1 -Configuration Release -Version "1.0.0.0" -OutputPath "release\installer" -Publisher "CN=Karol Mrozinski"
```

For Azure Trusted Signing:

```powershell
$env:AZURE_TENANT_ID = "..."
$env:AZURE_CLIENT_ID = "..."
$env:AZURE_CLIENT_SECRET = "..."
$env:AZURE_TRUSTED_SIGNING_ENDPOINT = "https://..."
$env:AZURE_TRUSTED_SIGNING_ACCOUNT_NAME = "..."
$env:AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME = "..."
./desktop/installer/build-msi.ps1 -Configuration Release -Version "1.0.0.0" -OutputPath "release\installer" -Publisher "CN=Karol Mrozinski" -UseAzureTrustedSigning
```

Without a signing credential, the package is still built, but it remains unsigned for local validation only.

## Release workflow

The GitHub Actions workflow in `.github/workflows/release-installer.yml` performs these steps:

1. installs Node.js and the dashboard dependencies
2. builds the dashboard production bundle
3. publishes the desktop launcher with .NET
4. assembles the MSI package from the app output
5. signs the installer using either PFX or Azure Trusted Signing when credentials are present
6. uploads the `.msi` artifact to the GitHub Actions run
7. attaches the package to a GitHub release when triggered by a release event

## Signing notes

- EV code signing is appropriate for public distribution and enterprise trust.
- Azure Trusted Signing is the best fit for cloud-managed signing in CI/CD workflows.
- WHQL/HLK are not generally required for a standard Windows desktop CTI application unless the product includes drivers or kernel-level system integration.
- ELAM/PPL are relevant only for deep system security components, not for a normal SaaS-style desktop workspace.
- MVI-related programs are only relevant for domains explicitly requiring the Microsoft validation path for security-critical or device-integrated software.

## Practical recommendation for this repo

For Sanctum Suite, the correct production posture is:

- use EV code signing or a comparable enterprise code-signing certificate for final customer trust;
- prefer Azure Trusted Signing in GitHub Actions for secure, automated signing;
- keep MSI/WiX as the shipping format for Windows installation;
- do not claim WHQL/HLK/ELAM/PPL as required for this app unless the product later adds kernel-driver or endpoint-protection functionality.

This is the most credible and least misleading combination for a CTI desktop product.
