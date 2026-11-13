# TPM 2.0 measured-boot gate with Keylime

Production and air-gapped API deployments require an operator-managed Keylime
verifier. Install and enroll a Keylime agent on the host running the Sanctum
service. Keylime, not this application, collects TPM 2.0 quotes and measured
boot evidence, checks them against approved reference state, and reports
attestation status. Sanctum queries the Keylime v2.5 verifier status API over
HTTPS with mutual TLS; it never reads TPM secrets or accepts caller-supplied
quotes as proof.

## Provision the verifier

1. Deploy a supported Keylime verifier and agent on the approved on-premises
   host. Enroll the agent and record its exact UUID.
2. Configure and review a TPM policy and measured-boot reference state for the
   host before trusting it. Keylime must report `has_mb_refstate: 1`; merely
   registering an agent or obtaining a TPM quote is not sufficient.
3. Issue a dedicated client certificate for Sanctum's status query. The
   default Keylime simple authorization provider treats trusted client
   certificates as administrators. If a read-only certificate is unavailable,
   expose the verifier through a separately controlled mTLS reverse proxy
   restricted to `GET /v2.5/agents/<configured-agent-uuid>` and isolate access
   to the verifier network. Do not put a general operator certificate in the
   application.
4. Install the verifier CA, client certificate, and matching private key as
   protected files readable by the unprivileged service identity. Do not put
   private key material in an image, environment variable, or release bundle.

## Configure Sanctum

Set the following environment variables:

| Variable | Purpose |
| --- | --- |
| `SANCTUM_TPM_VERIFIER_URL` | HTTPS base URL of the Keylime verifier or restricted proxy |
| `SANCTUM_TPM_AGENT_ID` | UUID of the enrolled host agent |
| `SANCTUM_TPM_CA_CERT_FILE` | Trusted CA bundle for verifier TLS |
| `SANCTUM_TPM_CLIENT_CERT_FILE` | mTLS client certificate |
| `SANCTUM_TPM_CLIENT_KEY_FILE` | Matching protected mTLS private key |
| `SANCTUM_TPM_MAX_ATTESTATION_AGE_SECONDS` | Maximum age of the last successful quote; default 120 seconds, allowed 10-3600 |

The client requests only `GET <base-url>/v2.5/agents/<agent-uuid>`. TLS
verification cannot be disabled and redirects are not followed. Readiness and
each authenticated `/api/v1` request fail closed unless Keylime returns HTTP
200 with `status: "Success"`, `attestation_status: "PASS"`,
`has_mb_refstate: 1`, and a non-future `last_successful_attestation` within the
configured age limit. The authorization audit records `keylime` alongside the
local RBAC/OPA engine when this check succeeds.

The included [Docker Compose profile](../docker-compose.yml) requires the
verifier URL and agent UUID and mounts the three certificate files as read-only
Compose secrets. Set `SANCTUM_TPM_VERIFIER_CA_SOURCE`,
`SANCTUM_TPM_CLIENT_CERT_SOURCE`, and `SANCTUM_TPM_CLIENT_KEY_SOURCE` to their
host-side file paths. Protect the private key on the host and verify that the
container's unprivileged UID can read it.

For rootless Podman, create secrets and set the corresponding `/run/secrets`
paths in the air-gapped environment file:

```sh
podman secret create sanctum-keylime-verifier-ca /secure/keylime-ca.pem
podman secret create sanctum-keylime-client-cert /secure/keylime-client.crt
podman secret create sanctum-keylime-client-key /secure/keylime-client.key
```

Add these secret mounts to `podman run`:

```sh
--secret id=sanctum-keylime-verifier-ca,target=/run/secrets/keylime-verifier-ca.pem,uid=10001,gid=10001,mode=0400 \
--secret id=sanctum-keylime-client-cert,target=/run/secrets/keylime-client-cert.pem,uid=10001,gid=10001,mode=0400 \
--secret id=sanctum-keylime-client-key,target=/run/secrets/keylime-client-key.pem,uid=10001,gid=10001,mode=0400 \
```

Then configure the URL, agent UUID, file paths, and a freshness limit in
`/etc/sanctum/airgap.env`. The operator's preflight command checks the same
fresh measured-boot status as the service readiness probe.

This gate establishes only that the configured Keylime verifier currently
reports a fresh passing quote for the configured agent and that a measured-boot
reference state is present. It does not independently validate the verifier,
reference-state provenance, firmware policy, the Sanctum container/image, or
the host's entire runtime; it is not hardware certification, Confidential
Computing, or an authorization to process classified data. Manage Keylime,
firmware baselines, revocation, agent updates, verifier backups, and network
isolation through the organization's approved process.
