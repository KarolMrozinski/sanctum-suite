# Secure CI/CD gates

The `ci.yml` workflow runs the regression suite, Python distribution build, and
dashboard lint/build. The separate `security.yml` workflow adds:

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
