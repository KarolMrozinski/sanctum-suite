# SANCTUM-SUITE Air-Gap Deployment Runbook

This runbook describes an operator-controlled deployment on a Linux host using
rootless Podman, an internal MinIO Object Lock service, and local evidence
verification. It is a procedural template, not a certified baseline or
accreditation. Approve the host OS/kernel, Podman and image versions, resource
limits, secret handling, access controls, retention mode, and recovery process
before use. For the full API container configuration, also follow
[the Podman air-gap deployment guide](./docs/PODMAN_AIRGAP.md).

## 1. Define and enforce the isolation boundary

1. Record the approved release tag, full source revision, destination host,
   authorized operators, intended container image digest, and allowed internal
   endpoints. Define the required retention and key-recovery procedures.
2. Prepare a dedicated Linux host or VM. Apply the approved OS baseline, host
   firewall rules, SELinux/AppArmor policy, encrypted storage, time source, and
   rootless Podman configuration. Restrict administrative access.
3. Establish an outbound-deny policy at the host/network boundary. Permit only
   explicitly approved internal services (for example OPA, Vault, MinIO,
   Keycloak, and Keylime) when required by the deployment. An internal DNS name
   or a Podman network marked `--internal` is not, by itself, proof that the
   host has no external route. Test and record denied external connections
   before loading workloads.
4. Keep deployment evidence, operator declarations, credentials, and audit
   exports inside the approved environment. Do not put secrets in command-line
   arguments, shell history, image layers, environment files committed to
   source control, or the release bundle.

## 2. Prepare and transfer an offline release

In the connected staging zone, use the approved CI/release process to build the
Python package and OCI image. Generate and review SBOMs, Trivy/Grype reports,
OPA test results, and the Cosign/in-toto attestation. Include the exact
artifacts, policy sources, local verification tools, and reports needed for the
offline operation in the release directory. Do not include credentials,
private keys, customer data, or unreviewed evidence.

Create and sign the file inventory on the authorized signing station:

```sh
sanctum offline-release-create /staging/release-bundle \
  --source-revision <full-git-commit> \
  --private-key-file /secure/offline/release-signing-ed25519.pem
```

Transfer the complete bundle on approved media and record chain of custody.
The public key and expected SHA-256 fingerprint must be supplied independently
of that media. Before unpacking, loading, or executing any bundle content, run
on the isolated destination:

```sh
sanctum offline-release-verify /media/release-bundle \
  --public-key-file /etc/sanctum/trusted-release-key.pem \
  --expected-signer-fingerprint <independently-confirmed-64-hex-fingerprint>
```

Stop on any verification error. Record the command output, verified
fingerprint, release revision, and operator. This verifies the signed
file inventory; it does not prove the source was benign, the build was
reproducible, the media was sanitized, or that supplied scan evidence is
complete. Load only the exact approved image archive after verification:

```sh
podman load --input /media/release-bundle/sanctum-suite.oci.tar
podman images --digests
```

Compare the loaded image digest with the independently approved release
record. Use a locally installed Sanctum package, OPA binary, Cosign binary,
policy files, and any scanner tools from the verified bundle; do not fetch
packages or container images from public registries in the isolated zone.

## 3. Configure MinIO Object Lock

Provision MinIO as an operator-managed service on protected, encrypted local
storage. Pin and verify the MinIO image version/digest, run it with the approved
rootless Podman identity, attach credentials through the organization's
secret-management mechanism, and restrict its network to authorized local
clients. Use TLS and the locally trusted CA. Do not use default credentials.

Create a **new** bucket with Object Lock enabled; Object Lock cannot be enabled
retroactively on an existing bucket. Using the locally installed MinIO client
and an already configured, protected alias:

```sh
mc mb --with-lock local/sanctum-audit-worm
mc retention set --default COMPLIANCE 7y local/sanctum-audit-worm
mc retention info local/sanctum-audit-worm
```

The `local` alias is an example: replace it with the approved internal MinIO
alias. Validate that the bucket reports Object Lock and the intended default
retention, then perform an authorized test write and confirm that deletion or
shortening of retention is denied for a test object. Record the results. Use a
dedicated service account with only the required permissions; protect its
secret and MinIO's root credentials separately. Compliance-mode retention may
be irreversible for the retention period: obtain data-owner/legal approval
before enabling it and test capacity, backup, restore, and expiry handling.

Configure the application to use the internal HTTPS endpoint, bucket, region,
CA certificate, and secret-file paths as described in
[the existing Podman guide](./docs/PODMAN_AIRGAP.md). Confirm that application
audit writes fail closed when MinIO is unavailable and that the first
authenticated operation verifies the WORM write. Object Lock protects stored
objects against alteration/deletion under its configured policy; it does not
make host logs, SQLite files, backups, or the deployment itself tamper-proof.

## 4. Stage and start runtime services

Provision the approved internal OIDC, Vault Transit, OPA, Keylime, Trustee
(when enabled), and MinIO services using their separately reviewed procedures.
Install and verify their CA bundles and service identities locally. Configure
the app with the protected secret files and non-secret endpoint settings
documented in [docs/PODMAN_AIRGAP.md](./docs/PODMAN_AIRGAP.md).

Create the rootless Podman network and persistent storage according to the
approved host policy. Where all dependencies are Podman services, an internal
network may be used as an additional boundary:

```sh
podman network create --internal sanctum-airgap
podman volume create sanctum-data
```

Attach only approved service containers to that network. If dependencies are
host services or reached through a controlled gateway, use the approved
firewall and routing design instead; do not assume an internal network can
reach them. Start the verified application image with read-only root
filesystem, dropped capabilities, `no-new-privileges`, a loopback-only
published API port, mounted CA/public configuration, and Podman secrets. Use
the tested command in [docs/PODMAN_AIRGAP.md](./docs/PODMAN_AIRGAP.md); do not
copy placeholder endpoints or credentials into production.

Verify TLS and `/readyz` from the host. Confirm OIDC, Vault Transit, MinIO
Object Lock, policy version, TPM measured-boot, and any configured confidential
computing verifier. Check host and Podman network policy independently. A
healthy endpoint is not evidence that an external network is unavailable or
that regulatory controls are satisfied.

## 5. Run local verification and collect reports

Run commands from the verified release directory or another access-controlled
working directory. Preserve their inputs and outputs as audit evidence. Use
operator-supplied JSON declarations for the readiness audit; it does not
independently inspect a kernel, Rust project, SPIRE deployment, or cryptographic
implementation. Example:

```sh
sanctum security-readiness --input ./evidence/readiness-declarations.json \
  > ./evidence/readiness-report.json
```

The supply-chain verifier checks the local artifact against the provided
Cosign/Sigstore in-toto bundle and the explicitly expected identity, issuer,
and predicate. It parses provided Trivy/Grype JSON but does not run scanners or
authenticate/bind their reports to the artifact:

```sh
sanctum supply-chain-verify \
  --artifact ./release/sanctum-suite.oci.tar \
  --attestation-bundle ./evidence/attestation.sigstore.json \
  --certificate-identity '<approved-signer-identity>' \
  --certificate-oidc-issuer '<approved-issuer>' \
  --predicate-type 'https://slsa.dev/provenance/v1' \
  --trivy-report ./evidence/trivy.json \
  > ./evidence/supply-chain-report.json
```

Trivy evidence is required for a complete executive report; add
`--grype-report ./evidence/grype.json` when a Grype report is also part of the
approved review.

Cosign verification may depend on trusted Sigstore roots or transparency-log
material. Stage and validate the exact trust material and Cosign version before
transfer. Prove in a network-denied rehearsal that this command succeeds using
only local material and fails closed when verification material is absent;
do not silently allow network access to make it pass. This CLI does not expose
a separate trust-root option, so use only the supported local configuration
for the staged Cosign version and document it.

Run the policy tests against the reviewed local Rego policy directory with the
staged OPA binary. `--fail-on-empty` makes an empty test suite a failure:

```sh
opa test --format=json --fail-on-empty ./policies \
  > ./evidence/opa-tests.json
```

Do not suppress a non-zero OPA exit code. Keep the raw output and command exit
status; run the executive aggregator only after reviewing whether every
required test ran successfully.

Generate the combined inspection report:

```sh
sanctum generate-executive-report \
  --readiness-report ./evidence/readiness-report.json \
  --supply-chain-report ./evidence/supply-chain-report.json \
  --opa-test-report ./evidence/opa-tests.json \
  --output-json ./evidence/executive-report.json \
  --output-markdown ./evidence/executive-report.md
```

The JSON retains the supplied reports; the Markdown provides a concise
summary. `REVIEW_REQUIRED` is intentionally conservative: missing scans,
failed/empty OPA tests, or readiness gaps/incomplete/unassessed domains require
human review. Even `EVIDENCE_COLLECTED` means only that the supplied evidence
met the aggregator's completeness checks; it is **not** a security verdict,
certification, or regulatory compliance finding. The scanner summaries are
not authenticated, and a passing OPA test suite does not establish policy
completeness.

## 6. Record, retain, and recover

Store the signed release manifest, tool versions, policy revision, command
lines, exit statuses, raw and aggregated reports, approvals, Object Lock
validation, and transfer/deployment records in the designated protected
evidence store. Avoid including credentials or unnecessary personal data.
Confirm report signatures and retention requirements using the organization's
separate report-signing procedure.

Back up the application data volume and MinIO data using an approved encrypted
process; test restoration on an isolated host. After restore, re-verify the
release/image digest, secret rotation, internal TLS, MinIO retention behavior,
OPA policy, verifier freshness, and outbound-deny controls before serving
requests. Document incidents, failed writes, retention exceptions, and
recovery decisions in the approved audit system.

Do not use this template for classified data or claim accreditation based only
on an air-gap label, Podman isolation, a passing report, or MinIO Object Lock.
