# Release Checklist

## Owner decisions

- Current restricted source-available license retained; legal/commercial review remains open.
- PLN is the preferred currency, but no price, billing period, or payment provider was approved.
- Lead form remains disabled by decision; no webhook endpoint or recipient was supplied.
- AWS provisioning is not approved; no region/domain was supplied and cloud-cost approval was declined.
- Privacy-controller details, support SLA, and security contact remain unspecified.
- EDR/SIEM remains vendor-neutral CEF/webhook only; no provider adapter was selected.
- Deployment remains local-only; no Parrot OS image digest or authorized lab was supplied.

## Product readiness

- [x] Package installs successfully with `pip install -e .`
- [x] Package builds successfully with `python -m build`
- [x] CLI commands work without terminal or Unicode crashes
- [x] Dashboard builds successfully
- [x] Test suite passes
- [x] Security and disclosure policy exists
- [x] Changelog is documented
- [x] Release documentation is present

## Launch requirements

- [ ] final legal review of licensing and commercial terms
- [ ] define customer support response SLA
- [x] draft GitHub release notes and define package assets
- [ ] publish an authorized GitHub release with wheel/sdist and checksums
- [ ] prepare a signed offline bundle containing the approved OCI image, SBOM, test/scan evidence, and deployment files; verify it with an independently trusted key
- [ ] document physical media custody and destination-side verification
- [x] prepare customer installation and deployment guide
- [ ] define pricing and sales handoff workflow
- [x] owner selected sales-led manual licensing with no online payments
- [ ] define approved commercial terms, any published PLN prices, and sales handoff
- [ ] configure and verify the lead webhook; publish a real sales contact path
- [ ] replace the website privacy template with reviewed, operator-specific information
- [ ] validate backups, secrets management, and environment isolation
- [ ] select and integrate a payment provider and license issuance/revocation workflow if selling subscriptions
- [x] implement signed offline entitlement verification and persistent usage metering
- [x] implement manual offline signed-token issuance for the selected sales-led model
- [ ] bind authenticated customers/API credentials to tenant-scoped storage and authorization before offering SaaS
- [ ] review all remaining demo/simulated module outputs before making customer-facing claims
- [ ] choose target AWS region/account/domain and approve cloud resource costs before provisioning

## Deployment safety

- [x] require explicit target allowlist, written authorization reference, and signed entitlement before active checks
- [ ] configure secure secret storage
- [ ] restrict API and dashboard exposure to trusted networks
- [ ] enable logging and audit trail capture
- [ ] define incident response contacts
- [ ] establish rollback and restore plan

## Release sign-off

A release is ready when all checkboxes above are complete and the production environment is validated by a responsible operator.
