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

## Required GitHub secrets

For signed production builds, configure these repository secrets:

- `WINDOWS_CERT_PFX_BASE64`
- `WINDOWS_CERT_PASSWORD`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TRUSTED_SIGNING_ENDPOINT`
- `AZURE_TRUSTED_SIGNING_ACCOUNT_NAME`
- `AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME`
- `AZURE_TRUSTED_SIGNING_POLICY` (optional)

The build script signs the generated MSI with either:

- a local PFX certificate via `signtool` and SHA-256 timestamping, or
- Azure Trusted Signing via the Azure CLI `az trusted-signing code-sign` command

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
