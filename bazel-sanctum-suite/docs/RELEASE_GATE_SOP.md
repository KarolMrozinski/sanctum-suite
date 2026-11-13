# Sanctum Suite Release Gate SOP

## 1. Purpose

This Standard Operating Procedure defines the formal release gate for Sanctum Suite signed Windows installer publication. It establishes the minimum controls required before a production MSI is approved for release to GitHub Releases and Windows distribution.

## 2. Scope

This SOP applies to the release of Sanctum Suite version v1.0.0 and all subsequent production releases that use the signed Windows installer path.

## 3. Roles and responsibilities

### 3.1 Release Manager
Responsible for version control, release branch status, artifact readiness, release publication, and final approval of publication.

### 3.2 Security
Responsible for validation of signing method, certificate validity, chain of trust, integrity of output artifact, and release governance alignment.

### 3.3 Owner
Responsible for final business approval and confirmation that the release is authorized for public publication.

### 3.4 Windows Validation
Responsible for validation of the final MSI on a clean Windows target, including install, launch, uninstall, and standard operational checks.

## 4. Release gate stages

### Gate 1: Build readiness

The Release Manager must confirm the following before the artifact enters the signing stage:

- repository target branch is approved
- release tag matches the intended version
- project version matches the release tag
- dependencies are restored successfully
- dashboard build is successful
- desktop packaging is successful
- MSI is generated successfully
- artifact naming is consistent with the release standard

### Gate 2: Signing readiness

Security must confirm the following before release approval:

- signing method is approved and selected
- certificate is valid and within its authorized validity window
- certificate chain is valid
- timestamping is enabled
- Azure Trusted Signing or enterprise certificate credentials are valid
- signing operation completes without error
- artifact is signed before publication

### Gate 3: Windows validation

Windows Validation must confirm the following on a clean Windows machine:

- the MSI installs successfully
- the application launches successfully
- the CTI dashboard opens without critical runtime errors
- required sections are visible and functional
- uninstall flow works correctly
- repair flow works correctly if applicable
- no trust or integrity warnings are present that would invalidate the distribution path

### Gate 4: Release publication

The Release Manager must confirm the following before publishing:

- GitHub release is created for the correct tag
- MSI artifact is attached
- checksum file is attached
- release notes are final and approved
- public release text matches the release artifact version
- release artifact is visible and downloadable

## 5. mandatory approval matrix

| Stage | Required approver | Required condition |
| --- | --- | --- |
| Build readiness | Release Manager | Build and artifact generation are complete |
| Signing readiness | Security | Signing method and trust chain are valid |
| Windows validation | Windows Validation | Clean install and launch validation complete |
| Final publication | Owner | Business and release approval complete |

## 6. release gate acceptance criteria

The release may proceed only when all required gates are passed and the approvers record their sign-off.

The release must not proceed if any of the following are true:

- build fails or generates an incomplete artifact
- signing fails or the certificate chain fails validation
- Windows validation fails on a clean target
- release notes or artifact metadata do not match the released version
- owner approval is not recorded

## 7. sign-off record

Release Manager sign-off: Approved / Rejected
Name: ______________________________
Date: ______________________________

Security sign-off: Approved / Rejected
Name: ______________________________
Date: ______________________________

Owner sign-off: Approved / Rejected
Name: ______________________________
Date: ______________________________

Windows Validation sign-off: Approved / Rejected
Name: ______________________________
Date: ______________________________

## 8. publish disposition

If any gate is rejected, the release must remain in draft or non-public status until the failure is corrected and all required approvals are obtained.

## 9. final enforcement

This SOP must be used as the final authorization gate for the publication of any signed Sanctum Suite installer to GitHub Releases or Windows distribution channels.
