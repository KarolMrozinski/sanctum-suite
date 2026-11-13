# Sanctum Suite production publication runbook for Windows target

## Purpose

This runbook defines the exact steps required to publish a signed Sanctum Suite Windows installer to GitHub Releases and verify it on a Windows target machine.

## Required prerequisites

- Windows build agent with access to signing credentials or Azure Trusted Signing
- GitHub repository with required secrets and variables configured
- WiX Toolset installed on the build runner
- Node.js 22 installed
- .NET 10 SDK installed
- permissions to create or update a GitHub release
- clean Windows target machine for validation

## Required repository configuration

### Secrets

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

### Variables

- `SIGNING_MODE` = `auto` or `azure-trusted-signing`
- `REQUIRE_SIGNED_BUILD` = `true`
- `BUILD_VERSION` = `1.0.0.0`
- `PUBLISHER` = `CN=Karol Mrozinski`
- `PRODUCT_NAME` = `Sanctum Suite`

## Release process

### Step 1: validate the branch and version

1. Ensure the repository is on the target release branch or tag.
2. Confirm that the version matches the release tag, for example `v1.0.0`.
3. Confirm the app is in the final release candidate state.

### Step 2: trigger the release workflow

Trigger the workflow using one of the following:

- `workflow_dispatch` in GitHub Actions
- push of a `v*` tag
- published GitHub release event

### Step 3: build the release artifact

The workflow should perform the following tasks automatically:

1. install Node.js 22
2. install .NET 10 SDK
3. install WiX Toolset
4. install dashboard dependencies
5. build the dashboard bundle
6. publish the Windows desktop launcher
7. generate the MSI installer
8. sign the MSI using the configured signing mode
9. generate a checksum manifest
10. upload the artifact bundle

### Step 4: verify the signing result

Before publication, confirm:

- the MSI file exists in `release/installer`
- the file is signed by the expected certificate
- the certificate chain is valid
- timestamping is present
- the hash manifest matches the MSI content

### Step 5: publish to GitHub Releases

1. Create or update the GitHub release tag, for example `v1.0.0`.
2. Attach the generated MSI and checksum file.
3. Publish the release notes from `.github/release-body.md`.
4. Confirm the release page shows the signed artifact and notes correctly.

### Step 6: validate on a clean Windows target

Use a clean Windows machine or VM with no previous Sanctum Suite installation:

1. download the MSI from the GitHub release page
2. run the installer
3. confirm installation completes without warnings that affect trust or integrity
4. launch the app
5. confirm the CTI dashboard loads and the key sections render correctly
6. validate the desktop shortcut and startup behavior
7. test uninstall / repair flow

## Final sign-off gate

A release is ready only when all of the following are complete:

- build succeeded
- signing succeeded
- certificate verification passed
- MSI installed successfully on a clean Windows host
- app starts correctly
- release notes are published
- artifact hash is reviewed
- product owner or authorized release manager approves publication

## Emergency rollback

If signing or installation validation fails:

1. stop publication immediately
2. keep the failed artifact unlisted or draft-only
3. investigate the signing or build issue
4. rerun the pipeline only after the certificate environment and artifact output are validated
5. do not publish unsigned or invalid installers as production artifacts

## Production recommendation

The recommended public release path is:

- EV Code Signing
- Azure Trusted Signing in GitHub Actions
- MSI/WiX installer format
- SHA-256 + timestamping
- verification on a clean Windows machine before final publish

This is the correct production model for Sanctum Suite.
