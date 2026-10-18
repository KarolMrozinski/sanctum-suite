# Control catalog and evidence records

SANCTUM-SUITE now exposes a small, version-labeled starter catalog through the authenticated API:

- `GET /api/v1/frameworks`
- `GET /api/v1/frameworks?category=methodology`
- `GET /api/v1/controls`
- `GET /api/v1/controls?framework=NIST%20CSF`
- `POST /api/v1/controls/{control_id}/assessments`
- `GET /api/v1/controls/{control_id}/assessments`
- `POST /api/v1/events/correlate`

Every endpoint requires `X-API-Key`. The initial catalog includes scoped references to OWASP ASVS 5.0.0, NIST CSF 2.0, CIS Controls 8.1, CWE Top 25 (2025), ISO/IEC 42001:2023, NIST AI RMF 1.0, NIST SP 800-53 Rev. 5, NIS2 Directive (EU) 2022/2555, and DORA Regulation (EU) 2022/2554. A reference is a discovery aid, not a claim that the control is equivalent to, satisfies, or certifies a framework requirement. PTES and OSSTMM editions and detailed test plans are not yet shipped as executable methodology packs. This starter catalog is not a complete implementation of those publications.

The frameworks endpoint also distinguishes standards, legislation, methodologies, threat models, cryptographic publications, and platform references, and labels whether a reference is metadata-only or has an implemented bounded behavior. It is not a control assessment or a downloadable complete methodology pack.

The same index includes public research sources such as Project Zero, Pwn2Own, Microsoft MSRC, Mandiant, NSA/NCSC advisories, and VX-Underground as references only. SANCTUM-SUITE does not scrape these sources, assert actor attribution from them, or download/distribute malware samples. Actor labels such as APT29, Sandworm, Equation Group, and Unit 26165 are planning context only; Stuxnet is historical context, not an executable test.

The event endpoint accepts up to 1,000 normalized events (`event_id`, `event_type`, `correlation_key`) and groups exact matching correlation keys locally. It does not establish a streaming connection or classify groups as threats. The SIEM helper can format CEF and can send only to an operator-configured HTTPS webhook; configure network egress controls because DNS resolution and webhook ownership remain deployment responsibilities. Sigma/YARA outputs are starter rules and require validation in the target product before use.

Assessment states are `verified`, `failed`, `needs_review`, `not_assessed`, and `not_applicable`. `verified` requires at least one evidence reference. Records retain a source label, caller-supplied reference, SHA-256 digest, assessor, timestamp, and summary; raw evidence content is not uploaded or persisted by this feature. A digest demonstrates identity only when independently recomputed against the evidence. It does not prove the evidence is accurate, complete, or authentic.

Example request:

```json
{
  "state": "verified",
  "summary": "The scoped control was retested against the approved baseline.",
  "assessed_by": "security-team",
  "evidence": [
    {
      "source": "approved-test-report",
      "reference": "artifact://assessment-123/report",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    }
  ]
}
```

Set `SANCTUM_CONTROLS_DB` to a durable, access-restricted SQLite path in deployments. The default is `~/.sanctum-suite/controls.sqlite3`. Back up this database and apply the organization's retention and access policies. It is a single-instance persistence mechanism, not a multi-tenant database or a substitute for tenant authorization, audit logging, or a production evidence repository.

The catalog does not automatically assess systems, collect evidence, decide legal applicability, or establish NIS2, DORA, ISO, NIST, DoD, NATO, or other compliance/certification status. The all-zero digest above is only a shape example and is not an evidence digest.

## Current capability boundaries

- Purple Team evaluation compares caller-supplied scenario/rule identifiers with supplied alerts. It does not execute attack techniques or connect to an EDR.
- eBPF enforcement is not implemented; the module reports prerequisites and never claims a kernel hook is active.
- PQC output classifies only an operator-supplied inventory against named NIST FIPS publications. It does not discover deployed cryptography or certify a migration.
- Offline transfer support can verify a supplied signature and creates a payload digest manifest only. It does not enforce a physical data diode or prove air-gap isolation.
- TEMPEST/SDIP-27 is not measured or certified by this software; evidence references remain subject to qualified review.
- Signed offline entitlements and persistent quota metering are implemented. Payment/checkout, license issuance/revocation, API-key-to-tenant binding, and durable per-customer data isolation remain unimplemented and require deployment/operator decisions.
- The Parrot integration reports only local OS/tool availability. It neither pins nor claims to run the newest Parrot OS image; select and verify an official image version and digest per lab before use.
