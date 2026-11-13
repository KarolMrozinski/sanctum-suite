# Air-gapped release bundle

This offline-bundle workflow signs and verifies the exact files in a release directory before physical transfer. It does not itself build or scan container images, generate an SBOM, establish source provenance, transfer media, or accredit the destination environment. The tag-triggered CI process described in [SECURE_CICD.md](./SECURE_CICD.md) builds the release artifacts, generates CycloneDX SBOMs, and attests their provenance; those outputs still need independent review before inclusion in an offline bundle.

## Prepare artifacts in the connected staging zone

Use an approved, isolated build host and record the complete source commit:

```sh
git rev-parse HEAD
python -m build --outdir release-bundle/python
podman save --format oci-archive \
  --output release-bundle/sanctum-suite.oci.tar \
  localhost/sanctum-suite:<release-tag>
```

Add the reviewed SBOM, dependency and container scan results, test/build reports, release notes, and deployment configuration templates to `release-bundle/`. These files must be generated and reviewed by the release process; the manifest tool only hashes and signs files already present. Do not include secrets, customer data, private keys, classified material, or unreviewed test data. The OCI archive includes its own image manifest and layers; record the intended image tag/digest in the release record as well.

Create an Ed25519 release-signing key through the organization's approved offline key ceremony. Keep the encrypted private key on the authorized signing station and distribute its public key and SHA-256 fingerprint through an independently trusted channel. Do not use the application's auto-generated report-signing key or a public key copied only from the transfer media.

On the signing station, create a detached signature over the complete file inventory:

```sh
sanctum offline-release-create release-bundle \
  --source-revision <full-git-commit> \
  --private-key-file /secure/offline/release-signing-ed25519.pem
```

For an encrypted PEM, the command prompts for its passphrase without echoing it. It writes `MANIFEST.json` and `MANIFEST.sig` alongside the artifacts and prints the signer's public-key fingerprint. The manifest contains each relative path, byte size, SHA-256 digest, source revision, creation time, and signer-key fingerprint.

## Transfer and verify in the isolated zone

Transfer the entire bundle using the organization's approved physical-media procedure. Record media identifiers, source/destination operators, timestamps, malware/content review, seal state, and custody hand-offs separately. Never treat this command as proof that the media is sanitized or that a data diode/air gap exists.

Before loading or executing any artifact, verify with the public key already trusted by the receiving organization and compare its fingerprint through the independent channel:

```sh
sanctum offline-release-verify /media/release-bundle \
  --public-key-file /etc/sanctum/trusted-release-key.pem \
  --expected-signer-fingerprint <independently-confirmed-64-hex-fingerprint>
```

Verification fails on a changed, missing, added, or unexpected file; an invalid Ed25519 signature; an untrusted signer fingerprint; or an unsafe bundle path. Only after successful verification should an operator load the image archive, for example:

```sh
podman load --input /media/release-bundle/sanctum-suite.oci.tar
```

Review the release record, SBOM and scan reports, target platform, configuration, and rollback plan before deployment. The signature proves that the corresponding private key signed the manifest; it does not prove who controlled that key, that the source was benign, that the build was reproducible, or that any included scan was complete.

## Operational limits

- Keep the signing private key offline and separate from build and deployment hosts.
- Protect the independently trusted public-key fingerprint and rotate keys through the organization's approved trust-update process.
- The verifier checks the exact directory inventory, but does not extract archives or inspect OCI layers.
- Re-signing an artifact set records a signer assertion; it does not replace CI provenance, SBOM validation, vulnerability triage, independent review, or a controlled release approval.
- This workflow does not make SANCTUM-SUITE approved for classified data or provide accreditation.
