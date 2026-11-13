# Sanctum Suite release readiness checklist

This checklist defines the minimum conditions required before a public Sanctum Suite Windows installer is treated as a production-ready, signed release artifact.

## 1. Product and build readiness

- [ ] Product identity remains Sanctum Suite and the UI branding is consistent across app/runtime/docs
- [ ] CTI dashboard and launch flow are working locally without broken navigation or missing sections
- [ ] `sanctum-dashboard` build completes successfully in CI or local validation
- [ ] desktop launcher publishes successfully and launches the app in a clean environment
- [ ] installer package is generated in the correct output folder
- [ ] output version matches the release tag and the expected product identity

## 2. Windows packaging readiness

- [ ] Windows runner is available for packaging and signing
- [ ] WiX Toolset is installed and available in the worker environment
- [ ] required .NET and Node.js toolchains are installed and version-validated
- [ ] MSI output is generated without warnings that affect installability or trust
- [ ] installer metadata includes correct product name, publisher, and version
- [ ] install and uninstall paths are tested in a clean Windows environment

## 3. Signing readiness

- [ ] chosen signing mode is explicitly defined (`auto`, `ev`, `azure-trusted-signing`, or enterprise/compliance mode)
- [ ] required certificate or Azure Trusted Signing credentials are available as GitHub secrets or environment values
- [ ] certificate thumbprint, CA chain, and timestamping are validated before publishing
- [ ] private key material is stored only in secure secret stores or HSM-backed infrastructure
- [ ] no certificate or private key is committed to the repo or included in build artifacts
- [ ] release artifacts are signed with SHA-256 and valid RFC3161 timestamping

## 4. GitHub Actions and release configuration

- [ ] repository/service secrets are populated and validated
- [ ] release variables are set in GitHub Actions or environment configuration
- [ ] workflow is configured to fail the release if `REQUIRE_SIGNED_BUILD=true` and signing is not available
- [ ] artifact upload is enabled for the generated MSI and any supporting files
- [ ] GitHub release is created only after successful build and signing validation

## 5. Security and compliance gate

- [ ] production output is signed before publication
- [ ] installer integrity is validated using a clean machine or signed verification process
- [ ] certificate chain and trust root are reviewed for the target distribution audience
- [ ] only advanced compliance paths are activated where the environment truly requires them
- [ ] WHQL, HLK, ELAM, PPL, MVI, NIAPC/NATO, FIPS 140-3, HSM Class 4, and NSA Type 1 modes remain environment-conditional and are not treated as default requirements for the standard app

## 6. Release sign-off

- [ ] final build artifact has been validated on a clean Windows machine
- [ ] install path, launch behavior, and app startup are confirmed
- [ ] uninstall path or repair path is confirmed
- [ ] final release notes describe the signing mode and trust model used
- [ ] release manager approves publication
- [ ] artifact publication is approved only after the signed verification step passes

## 7. Production release recommendation

For the public release of Sanctum Suite, the recommended and most credible model is:

1. EV Code Signing for public trust and final release identity
2. Azure Trusted Signing as the cloud-managed signing service in GitHub Actions
3. MSI/WiX installer as the native Windows package format
4. SHA-256 + timestamping for artifact integrity and verification
5. optional advanced security/compliance modes only when a target environment specifically requires them

A production release is not considered final until every item above is satisfied and the signed artifact has been verified in a trusted Windows environment.
