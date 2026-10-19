# Secure CI/CD gates

The `ci.yml` workflow tests the Rego authorization policy with OPA, model-checks
the authorization/audit TLA+ specification with TLC, runs the regression suite,
builds the Python distribution, and lints/builds the dashboard. The separate
`security.yml` workflow adds:

- Bandit static analysis for Python at medium-or-higher severity and confidence.
- `pip-audit` for known Python dependency vulnerabilities.
- Gitleaks scanning across repository history for committed credentials.
- Bounded Hypothesis property tests for IP target normalization and JSON, JSONL,
  and CEF telemetry parsers.
- OWASP ZAP passive baseline scanning of the local API documentation surface on
  an ephemeral GitHub-hosted runner. The DAST job does not accept or scan
  arbitrary target hosts; warnings are retained in the report and high-risk
  failures block the job. This is a bounded unauthenticated scan, not a full
  authenticated API penetration test.
- Trivy scanning of the locally built container for high/critical vulnerabilities,
  secrets, and image misconfiguration, while producing a CycloneDX image SBOM.

Python security reports, the DAST report, and the image SBOM are retained as
workflow artifacts for 30 days. Do not upload production datasets, credentials,
or classified material to CI artifacts. CI uses synthetic test data only.

The `release-sbom.yml` workflow runs only for `v*` tags. It builds the Python
wheel/sdist, a standalone dashboard archive, and a local OCI image archive;
generates a CycloneDX SBOM for each; and creates a digest manifest linking each
SBOM to its release artifacts and recording the container image ID. It compares
each SBOM to the latest published GitHub release when it contains all three
SBOM assets; otherwise the report records that no baseline SBOM was available.
A changed dependency is reported for review and does not by itself block
publication.

GitHub artifact attestations use short-lived Sigstore identities to sign both
the SBOM-to-artifact relationship and build provenance. A separate job verifies
those attestations before `gh release create` publishes any assets. This requires
GitHub artifact attestations to be enabled and available for the repository's
visibility/plan. The CI signature is an identity/provenance assertion, not an
offline release-key signature or evidence that the source, dependency inventory,
or scan result is correct. Consumers should independently verify attestations
against the expected repository/workflow and review SBOM diffs and scan results.
GitHub Actions workflow artifacts are retained for 90 days; published release
assets persist according to repository release policy.

Dependabot checks Python, dashboard npm, and GitHub Actions dependencies weekly.
Review update PRs and their tests; dependency automation is not authorization
to deploy a change. Configure repository branch protection to require the
`test`, `Python SAST and dependency audit`, `Secret detection`,
`Property-based parser fuzzing`, `Local application DAST`, and
`Container vulnerability scan and SBOM` checks before merging to `main`.

Scanner findings are not silently suppressed. If a finding is a verified false
positive, document the rule, affected code, rationale, reviewer, and expiry in a
narrow, version-controlled exception and revalidate it periodically. These
checks reduce risk but do not prove the absence of vulnerabilities or establish
certification.
