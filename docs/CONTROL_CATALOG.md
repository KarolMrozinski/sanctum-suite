# Control catalog and evidence records

SANCTUM-SUITE now exposes a small, version-labeled starter catalog through the authenticated API:

- `GET /api/v1/frameworks`
- `GET /api/v1/frameworks?category=methodology`
- `GET /api/v1/controls`
- `GET /api/v1/controls?framework=NIST%20CSF`
- `GET /api/v1/controls/coverage`
- `GET /api/v1/controls/coverage?framework=CWE%20Top%2025`
- `GET /api/v1/controls/mappings/history`
- `POST /api/v1/controls/{control_id}/assessments`
- `GET /api/v1/controls/{control_id}/assessments`
- `POST /api/v1/events/correlate`

Every endpoint requires `X-API-Key`. The internal catalog currently reports version `1.0.0`; assessments record the internal version against which they were made. Every mapped relationship is snapshotted in `control_catalog_mappings` with an immutable mapping ID, catalog version, source publication/version, reference, and relation type. Mapping history is append-only; catalog maintainers must increment the internal catalog version when changing mappings so later snapshots do not rewrite earlier history. The initial catalog includes scoped references to OWASP ASVS 5.0.0, NIST CSF 2.0, CIS Controls 8.1, CWE Top 25 (2025), ISO/IEC 42001:2023, NIST AI RMF 1.0, NIST SP 800-53 Rev. 5, NIS2 Directive (EU) 2022/2555, and DORA Regulation (EU) 2022/2554. References are intentionally broad and use `related` mappings; they are not imported or transcribed official requirement text and do not claim equivalence, satisfaction, or certification. PTES and OSSTMM editions and detailed test plans are not yet shipped as executable methodology packs. This starter catalog is not a complete implementation of those publications.

The coverage endpoint provides a versioned, SHA-256-digested snapshot of the catalog's current related mappings and the latest operator-entered assessment for each mapped control. Assessment states are control-level; when a control maps to multiple publications, the same latest control assessment appears in each related row. Rows marked `not_assessed` are identified gaps in the tool's assessment records, not evidence that the organization lacks the corresponding security measure. The report does not decide legal applicability or provide a compliance percentage or certification.

The frameworks endpoint also distinguishes standards, legislation, methodologies, threat models, cryptographic publications, and platform references, and labels whether a reference is metadata-only or has an implemented bounded behavior. It is not a control assessment or a downloadable complete methodology pack.

The same index includes public research sources such as Project Zero, Pwn2Own, Microsoft MSRC, Mandiant, NSA/NCSC advisories, and VX-Underground as references only. SANCTUM-SUITE does not scrape these sources, assert actor attribution from them, or download/distribute malware samples. Actor labels such as APT29, Sandworm, Equation Group, and Unit 26165 are planning context only; Stuxnet is historical context, not an executable test.

The event endpoint accepts up to 1,000 normalized events (`event_id`, `event_type`, `correlation_key`) and groups exact matching correlation keys locally. It does not establish a streaming connection or classify groups as threats. The SIEM helper can format CEF and can send only to an operator-configured HTTPS webhook; configure network egress controls because DNS resolution and webhook ownership remain deployment responsibilities. Sigma/YARA outputs are starter rules and require validation in the target product before use.

Assessment states are `verified`, `failed`, `needs_review`, `not_assessed`, and `not_applicable`. `verified` requires at least one evidence reference. Records retain the internal catalog version, a source label, caller-supplied reference, SHA-256 digest, assessor, timestamp, and summary; raw evidence content is not uploaded or persisted by this feature. A digest demonstrates identity only when independently recomputed against the evidence. It does not prove the evidence is accurate, complete, or authentic.

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

- Purple Team replay compares an expected scenario/rule pair with source-provided detection identifiers already attached to a case timeline. Results are append-only and included in authenticated case reports. This is metadata matching only: it does not execute attack techniques, validate that a scenario ran, or connect to an EDR.
- eBPF enforcement is not implemented; the module provides a planning checklist, not kernel inspection or an active hook.
- The PQC CLI reviews an operator-supplied inventory, classifies selected algorithm names, and can flag explicitly declared long-term key-establishment use for migration triage. It does not discover deployed cryptography or certify a migration.
- Offline transfer support verifies a supplied payload signature and emits payload and canonical manifest digests with a signer-key fingerprint. It does not transfer data, authenticate key ownership or manifest provenance, enforce a physical data diode, or prove air-gap isolation.
- TEMPEST/SDIP-27 handling records evidence-reference presence only; measurement, applicability, accreditation, and compliance remain for qualified review.
- Signed offline entitlements and persistent quota metering are implemented. Payment/checkout, license issuance/revocation, API-key-to-tenant binding, and durable per-customer data isolation remain unimplemented and require deployment/operator decisions.
- The Parrot preflight checks an operator-supplied local ISO against an operator-supplied SHA-256 and reports host executable availability only. It does not authenticate checksum provenance, inspect image packages, provision or isolate a VM, or launch tests. Follow the [Parrot lab preflight guide](./PARROT_LAB.md) and independently verify the official image release.
