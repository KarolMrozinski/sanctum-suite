# Air-gapped deployment with rootless Podman

This is a deployment template for a Linux VM with rootless Podman. It is not a certified baseline. Approve the Linux distribution/version, Podman version, host kernel, systemd policy, storage encryption, SELinux/AppArmor, network policy, and resource limits with the lab owner before deployment.

## Verify and load the image

Build and scan the OCI image in the connected staging zone, add it and its SBOM/test/scan evidence to an offline release bundle, then sign the bundle using the process in [OFFLINE_RELEASE.md](./OFFLINE_RELEASE.md). On the destination, verify the bundle using the public key and fingerprint trusted by the organization before loading:

```sh
sanctum offline-release-verify /media/release-bundle \
  --public-key-file /etc/sanctum/trusted-release-key.pem \
  --expected-signer-fingerprint <independently-confirmed-fingerprint>
podman load --input /media/release-bundle/sanctum-suite.oci.tar
```

Use the exact image reference recorded in the approved release record. Restrict the host's egress to the approved Keycloak, Vault, and MinIO endpoints; the application itself does not establish host network isolation.

## Provision runtime secrets and data

Create the API TLS certificate/key, Vault token, MinIO service-account key/secret, and report-signing private key as Podman secrets from independently controlled files. The API certificate must chain to the mounted trusted CA and include `localhost` as a DNS subject alternative name so the container health check can verify it. Do not put secret contents in a shell command, image, release bundle, or checked-in environment file:

```sh
podman secret create sanctum-api-tls-cert /secure/api-cert.pem
podman secret create sanctum-api-tls-key /secure/api-key.pem
podman secret create sanctum-vault-token /secure/vault-token
podman secret create sanctum-minio-access-key /secure/minio-access-key
podman secret create sanctum-minio-secret-key /secure/minio-secret-key
podman secret create sanctum-report-signing-key /secure/report-signing-private.pem
podman secret create sanctum-audit-pseudonym-key /secure/audit-pseudonym.key
```

The report-signing public key and trusted CA bundle are public configuration, but must still be installed from approved sources. The signing key is separate from the Ed25519 key used to sign offline release manifests.

Create `/etc/sanctum/airgap.env` with non-secret deployment settings and access limited to the service operator:

```sh
SANCTUM_ENVIRONMENT=air-gapped
SANCTUM_OIDC_ISSUER=https://keycloak.internal/realms/lab
SANCTUM_OIDC_AUDIENCE=sanctum-api
SANCTUM_OIDC_CA_CERT=/etc/sanctum/pki/internal-ca.pem
SANCTUM_KMS_BACKEND=vault-transit
SANCTUM_VAULT_ADDR=https://vault.internal:8200
SANCTUM_VAULT_TOKEN_FILE=/run/secrets/vault-token
SANCTUM_VAULT_TRANSIT_MOUNT=transit
SANCTUM_VAULT_TRANSIT_KEY=sanctum-payload
SANCTUM_VAULT_CA_CERT=/etc/sanctum/pki/internal-ca.pem
SANCTUM_IMMUTABLE_AUDIT_ENABLED=true
SANCTUM_AUDIT_PSEUDONYM_KEY_FILE=/run/secrets/audit-pseudonym-key
SANCTUM_AUDIT_S3_ENDPOINT=https://minio.internal
SANCTUM_AUDIT_S3_BUCKET=sanctum-audit-worm
SANCTUM_AUDIT_S3_REGION=us-east-1
SANCTUM_AUDIT_S3_ACCESS_KEY_FILE=/run/secrets/minio-access-key
SANCTUM_AUDIT_S3_SECRET_ACCESS_KEY_FILE=/run/secrets/minio-secret-key
SANCTUM_AUDIT_S3_CA_CERT=/etc/sanctum/pki/internal-ca.pem
SANCTUM_REPORT_SIGNING_PRIVATE_KEY_FILE=/run/secrets/report-signing-private.pem
SANCTUM_REPORT_SIGNING_PUBLIC_KEY_FILE=/etc/sanctum/report-signing-public.pem
SANCTUM_TLS_CERT_FILE=/run/secrets/api-cert.pem
SANCTUM_TLS_KEY_FILE=/run/secrets/api-key.pem
SANCTUM_TLS_CA_CERT=/etc/sanctum/pki/internal-ca.pem
SANCTUM_TENANT_DATA_DIR=/data/tenants
SANCTUM_CASES_DB=/data/cases.sqlite3
SANCTUM_CONTROLS_DB=/data/controls.sqlite3
SANCTUM_BILLING_DB=/data/usage.sqlite3
```

The file contains paths and endpoint names, not credentials. Podman secret targets must use these `/run/secrets/...` names and be readable only by the image's unprivileged UID/GID `10001`. Verify Podman's actual secret UID/GID behavior on the approved host before accepting the deployment.

## Start the container

Create an encrypted, access-restricted persistent data volume owned by the container's unprivileged user in the rootless user namespace. Use the tested host procedure for UID/GID mapping and SELinux labeling; do not use `chmod 777`. Then launch the verified image:

```sh
podman run --detach \
  --name sanctum-suite \
  --restart=unless-stopped \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --workdir /data \
  --volume sanctum-data:/data:Z \
  --volume /etc/sanctum/pki/internal-ca.pem:/etc/sanctum/pki/internal-ca.pem:ro,Z \
  --volume /etc/sanctum/report-signing-public.pem:/etc/sanctum/report-signing-public.pem:ro,Z \
  --secret id=sanctum-api-tls-cert,target=/run/secrets/api-cert.pem,uid=10001,gid=10001,mode=0400 \
  --secret id=sanctum-api-tls-key,target=/run/secrets/api-key.pem,uid=10001,gid=10001,mode=0400 \
  --secret id=sanctum-vault-token,target=/run/secrets/vault-token,uid=10001,gid=10001,mode=0400 \
  --secret id=sanctum-minio-access-key,target=/run/secrets/minio-access-key,uid=10001,gid=10001,mode=0400 \
  --secret id=sanctum-minio-secret-key,target=/run/secrets/minio-secret-key,uid=10001,gid=10001,mode=0400 \
  --secret id=sanctum-report-signing-key,target=/run/secrets/report-signing-private.pem,uid=10001,gid=10001,mode=0400 \
  --secret id=sanctum-audit-pseudonym-key,target=/run/secrets/audit-pseudonym-key,uid=10001,gid=10001,mode=0400 \
  --env-file /etc/sanctum/airgap.env \
  --publish 127.0.0.1:8000:8000 \
  --cap-drop=all \
  --security-opt=no-new-privileges \
  <approved-image-reference>
```

The API uses TLS in the container and is published only on host loopback. Place an explicitly configured TLS-terminating proxy in front of it if remote clients are required; do not publish the API directly to a general network. Check `https://localhost:8000/readyz` from the host. Production readiness requires OIDC, Vault Transit, the audit pseudonymization key, a valid RSA report-signing key pair, and reachable MinIO Object Lock configuration. The first authenticated API operation additionally verifies its WORM write; on failure, that operation is not executed.

## Recovery and operation

Back up the `/data` volume using an approved, encrypted, access-controlled process and test restoration on an isolated host. SQLite tenant files, local incident data, and local audit records are not automatically encrypted by Vault Transit. A restored service must revalidate identity mappings, secret rotation, MinIO WORM behavior, Vault key recovery, TLS, and image provenance before serving requests. Monitor MinIO failures and HTTP 503 responses; a failed completion audit can mean the route executed but its final audit object did not persist.

Do not deploy this template with classified payloads or infer authorization/accreditation from container isolation, Object Lock, or a passing readiness probe.
