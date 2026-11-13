# Final publication checklist for signed Sanctum Suite MSI

## 1. Pre-release validation

- [ ] repository is on the intended release branch or tag
- [ ] project version matches the GitHub release tag
- [ ] dashboard build succeeds
- [ ] desktop publish succeeds
- [ ] MSI package is generated successfully
- [ ] signing credentials are valid and authorized for production
- [ ] required GitHub secrets and variables are populated in the target environment

## 2. Code signing validation

- [ ] chosen signing mode is confirmed (`auto`, `ev`, `azure-trusted-signing`, or enterprise mode)
- [ ] certificate chain is valid
- [ ] timestamping is enabled and valid
- [ ] signing step succeeds on the Windows release runner
- [ ] output artifact is signed before upload

## 3. Installer verification

- [ ] MSI installs on a clean Windows machine
- [ ] app launches on first-run without missing dependencies
- [ ] no missing or broken visual assets or configured routes
- [ ] desktop shortcut and uninstall flow behave correctly
- [ ] all expected CTI sections render in the app

## 4. Release publication

- [ ] GitHub release draft is prepared
- [ ] public release artifact is attached
- [ ] checksum file or signature verification details are included
- [ ] release notes are published and consistent with the artifact version
- [ ] if needed, security contact and support note are linked in the release body

## 5. Post-publication monitoring

- [ ] installer download is validated from the release page
- [ ] support and feedback channel is monitored after publication
- [ ] any issues discovered post-release are triaged and tracked

## 6. Final sign-off

- [ ] product owner approves the release
- [ ] signing and security review approves the final artifact
- [ ] final release is published only after all checks above pass

This is the final operational checklist before a production signed MSI is published to GitHub Releases for Windows distribution.
