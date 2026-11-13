# Sanctum Suite signing policy

This document defines the production signing and certification posture for the Sanctum Suite Windows installer and release pipeline. The goal is to be honest, production-ready, and aligned with real Microsoft and enterprise signing requirements without claiming that every certificate path is required for a standard CTI desktop application.

## 1. Recommended production path

For the Sanctum Suite production release, the recommended and most credible signing path is:

1. EV Code Signing certificate for the public release identity
2. Azure Trusted Signing as the cloud-managed signing platform in CI/CD
3. SHA-256 signing with RFC3161 timestamping
4. MSI/WiX as the primary Windows installer format
5. Signed release artifacts only in the official GitHub release pipeline

This matches the reality of modern Windows software distribution and remains valid for a desktop CTI product without requiring the deeper Microsoft driver or kernel certification stack.

## 2. Why EV and Azure Trusted Signing are the best default

### EV Code Signing

EV Code Signing provides:
- stronger trust and higher assurance for public software distribution
- better customer confidence for enterprise-managed installations
- a stronger identity posture for a commercially distributed application

### Azure Trusted Signing

Azure Trusted Signing is the best operational fit for CI/CD because it:
- keeps private keys outside the build runner
- reduces exposure of signing secrets in ephemeral environments
- supports automated signing in cloud-hosted release pipelines
- pairs well with GitHub Actions and enterprise release controls

## 3. Certification modes supported by the project

The repository is intentionally prepared for the following future certification and validation modes, but they are not all required for a normal CTI desktop product.

### X.509 certificate support

Use when:
- a PKI-issued certificate chain is managed by the organization
- identity binding must follow a standard X.509 certificate lifecycle
- the app is distributed under an enterprise-managed certificate trust model

This is broadly compatible with private CA, public CA, and enterprise trust anchors. The repository’s signing scripts accept certificate-based flows through PFX/Thumbprint-based signing and can be extended to enterprise PKI issuance templates.

### mTLS / mutual TLS support

Use when:
- the signing authority requires mutual authentication
- the build or release gateway must authenticate using both client and server certificates
- the enterprise regulates certificate-based secure channel validation for release operations

The build flow supports a prepared mTLS path where a client certificate and CA bundle can be connected to a secure release gateway or signing service.

### Root CA and enterprise PKI support

Use when:
- the organization operates a private PKI or enterprise root CA
- software distribution requires enterprise trust anchoring
- certificates must be issued according to internal issuance and revocation standards

The project supports a BYO-PKI and root-CA model for enterprise-controlled signing trust chains.

### BYO-PKI support

Use when:
- the organization wants to supply its own certificate authority policies
- signing must follow internal policy, issuance boundaries, and compliance controls
- the environment is kept offline or private for regulated deployment

This is treated as a fully supported future deployment mode rather than a requirement for standard public distribution.

### FIPS 140-3 cryptographic module support

Use when:
- the signing environment must use a FIPS 140-3 validated cryptographic module
- hardware or software cryptographic operations must satisfy federal or regulated requirements
- the release process needs HSM-backed key protection and compliant crypto modules

This repository supports the policy and build path for FIPS 140-3-aware environments, even though actual validated module use requires a compliant operational environment and hardware or software configuration.

### NIAPC / NATO-related secure platform support

Use when:
- the environment is part of a nationally or alliance-governed secure computing posture
- the software must align with a secure national or defense-oriented PKI profile
- release policy must satisfy a dedicated regulated profile beyond standard enterprise distribution

This is not a default requirement for Sanctum Suite, but the project supports a clearly separated policy path for such environments.

### HSM-class security support (FIPS 140-3 Level 4)

Use when:
- the organization requires hardware-backed cryptographic protection at high assurance level
- keys must stay inside a validated HSM boundary
- release signing requires strong tamper resistance and key custody controls

This mode is included as a future-ready path for high-assurance enterprise or defense deployment, not as a default requirement for a standard CTI desktop app.

### EV Code Signing

Use when:
- distributing the installer to customers or enterprise users
- the product needs a public-facing signed identity
- the release is expected to be trusted broadly on Windows

Required environment variables:
- `WINDOWS_CERT_THUMBPRINT` or `WINDOWS_CERT_PFX_BASE64` + `WINDOWS_CERT_PASSWORD`
- `SIGNING_MODE=ev` or `auto`

### Azure Trusted Signing

Use when:
- release signing is managed centrally in Azure
- the organization wants cloud-hosted key custody and automated signing
- GitHub Actions must sign the MSI without storing the private key in the workflow

Required environment variables:
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TRUSTED_SIGNING_ENDPOINT`
- `AZURE_TRUSTED_SIGNING_ACCOUNT_NAME`
- `AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME`
- optional: `AZURE_TRUSTED_SIGNING_POLICY`

### WHQL

WHQL applies primarily to:
- driver signing
- hardware-related validation
- kernel-mode or Microsoft hardware certification paths

For Sanctum Suite, WHQL is only relevant if the product introduces drivers, kernel components, or hardware-dependent installation patterns. A standard desktop CTI app does not normally need WHQL.

### HLK

HLK is relevant for:
- hardware and device certification validation
- Windows hardware compliance testing in lab environments

This is not a standard requirement for a software-only CTI application unless the product is interacting with hardware or device-specific Windows integration scenarios.

### ELAM

ELAM is relevant for:
- kernel-level security integration
- early-launch anti-malware or system-protection components
- operating-system security stack integration

This is not required for a typical desktop CTI workspace unless the application is being deployed as a kernel-level security component.

### PPL

PPL applies to:
- protected-process scenarios
- high-integrity security components
- operating-system protected execution environments

This is not a normal requirement for a desktop CTI dashboard product unless the application is explicitly designed as a protected system security component.

### MVI

MVI-related Microsoft validation programs are for:
- specific Microsoft security or validation programs
- product programs with explicit Microsoft-partner requirements
- system-integration programs with formal validation obligations

This is not a relevant default requirement for Sanctum Suite unless the product is specifically participating in a targeted Microsoft validation track.

## 4. Production recommendation for Sanctum Suite

The recommended production posture is:

- use EV Code Signing for the final public release identity
- use Azure Trusted Signing as the CI/CD signing service
- ship the Windows install as an MSI/WiX package
- use SHA-256 signing and RFC3161 timestamping
- keep WHQL/HLK/ELAM/PPL/MVI as conditional or future validation paths, not mandatory project requirements

This is the most accurate and least misleading release strategy for a CTI platform that is primarily a desktop application and analytics workspace rather than a kernel or hardware component.

## 5. Release environment requirements

The following conditions should be met before a production release is considered final:

- a Windows-hosted build agent or equivalent Windows signing environment
- valid EV certificate or Azure Trusted Signing credentials
- trusted timestamping service
- minimal artifact integrity verification
- a GitHub Actions release pipeline configured with signing secrets or variables
- a secure verification and rollback process for release artifacts

## 6. Required repository variables and secrets

### Recommended GitHub repository secrets

- `WINDOWS_CERT_PFX_BASE64`
- `WINDOWS_CERT_PASSWORD`
- `WINDOWS_CERT_THUMBPRINT`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TRUSTED_SIGNING_ENDPOINT`
- `AZURE_TRUSTED_SIGNING_ACCOUNT_NAME`
- `AZURE_TRUSTED_SIGNING_CERT_PROFILE_NAME`
- `AZURE_TRUSTED_SIGNING_POLICY`

### Recommended GitHub repository variables

- `SIGNING_MODE` = `auto` or `azure-trusted-signing` for production CI
- `REQUIRE_SIGNED_BUILD` = `true` for final public releases

## 7. Decision rule

The release policy should be:

- if the release is public and customer-facing, prefer EV + Azure Trusted Signing
- if a specific Microsoft validation program is required, use the relevant certification mode
- if the environment is not ready for full signing, build the MSI but keep it explicitly marked as validation-only and do not publish it as a production artifact

## 8. Policy statement

Sanctum Suite will not claim that WHQL, HLK, ELAM, PPL, or MVI are required for the base product unless the product architecture or legal/compliance environment explicitly requires them. The project remains compatible with those modes in principle, but the standard desktop CTI release posture is EV + Azure Trusted Signing with a signed MSI/WiX package.

## 9. Final recommendation

For the Sanctum Suite production release, the final recommended combination is:

- EV Code Signing
- Azure Trusted Signing in CI/CD
- SHA-256 signing with timestamping
- MSI/WiX packaging
- conditional future WHQL/HLK/ELAM/PPL/MVI compatibility for specific enterprise or Microsoft-program scenarios

This is the correct balance between security, credibility, and honest product maturity.
