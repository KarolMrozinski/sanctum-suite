# SANCTUM-SUITE

<div align="center">
  <p>
    <img src="https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" />
    <img src="https://img.shields.io/badge/FastAPI-API-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Status-beta-f59e0b?style=flat-square" alt="Beta" />
    <img src="https://img.shields.io/badge/Docs-OpenAPI-2563eb?style=flat-square" alt="OpenAPI" />
  </p>
</div>

## Why SANCTUM-SUITE was created

Modern security programs often fail not because the right tools are missing, but because the environment lacks grounded evidence, explicit trust boundaries, and clear operator intent. SANCTUM-SUITE was created to give organizations a structured way to define what is being verified, what evidence exists, and what remains untrusted or unconfigured before live integration is considered.

The project is designed for controlled, high-assurance environments where governance, auditability, and evidence quality matter as much as tooling capability. It turns a security stack into a reviewable model of trust and evidence collection instead of a vague list of technologies.

## Core product pillars

<table>
  <tr>
    <td><a href="#platform-catalog"><strong>Platform catalog</strong></a><br/>Operator-managed inventory of technologies, systems, and capability surfaces.</td>
    <td><a href="#security-capability-model"><strong>Security capability model</strong></a><br/>Normalized mapping from technologies to evidence-backed security functions.</td>
  </tr>
  <tr>
    <td><a href="#api-contract"><strong>API contract</strong></a><br/>REST endpoints for capability discovery, evidence exchange, and controlled sync.</td>
    <td><a href="#documentation"><strong>Documentation</strong></a><br/>Detailed notebook, OpenAPI contracts, and adapter examples for future integration.</td>
  </tr>
</table>

## Platform catalog

The project maintains a structured catalog of technology surfaces that may later be bound to real telemetry, attestation, and policy evidence.

- Binary analysis and reversing: Ghidra, BAM, HIRS, paccor, RIM-Tool
- OS and runtime integrity: HP-UX, Oracle Solaris, OpenVMS, SELinux, VxWorks
- Signals, intelligence, and monitoring: GRASSMARLIN, ELITEWOLF, WALKOFF, PRISM, XKeyscore, Boundless Informant
- Cloud and infrastructure: C2S, JWCC, Mandiant Advantage, Mandiant Automated Defense, Google Cloud Platform (GCP)
- Mission and control systems: US-984XN (official SIGAD designation for the PRISM signals intelligence program)
- Software and data platforms: C/C++, Go, Assembly, Apache Accumulo, Apache Hadoop, Spark, Kafka, ELK Stack, Terraform
- AI and emerging hardware: Sec-PaLM, Palantir Gotham / Foundry, QKD, Intel Loihi, IBM TrueNorth, GNN, Agentic AI, DNA Data Storage

This catalog remains evidence-first by design: technologies are modeled as capability surfaces, not as guaranteed live integrations.

## Security capability model

SANCTUM-SUITE maps technologies to normalized security capabilities such as:

- `security-capability:binary-analysis`
- `security-capability:runtime-attestation`
- `security-capability:linux-integrity`
- `security-capability:gcp-platform`
- `security-capability:terraform-policy`
- `security-capability:observability`
- `security-capability:mission-integration`

Each capability includes:

- stable identifier
- source type and trust boundary
- expected evidence format
- integration mode: `PLAN_ONLY`, `CONFIGURED`, `LIVE`
- operator-controlled trust context

## API contract

The repository exposes an explicit REST surface for future data binding and evidence handling:

- `GET /api/v1/security-capabilities`
- `GET /api/v1/security-capabilities/{capability_id}`
- `POST /api/v1/security-capabilities`
- `GET /api/v1/security-capabilities/{capability_id}/evidence`
- `POST /api/v1/security-capabilities/{capability_id}/evidence`
- `POST /api/v1/security-capabilities/{capability_id}/sync`

The system is intentionally fail-closed: without explicit configuration or credentials, it remains in a safe review-only mode rather than pretending to be connected to live operational sources.

## Glossary

### US-984XN / PRISM

`US-984XN` is the official SIGAD designation associated with the PRISM signals intelligence program. In this repository, the capability is represented as a live mission-control adapter, `security-capability:mission-integration`, and is configured for active runtime evidence exchange with operator-managed mission context, attestation validation, and telemetry correlation. When the upstream mission system is connected, the integration is intended to operate as a real live data path rather than a review-only placeholder.

## Documentation

- Deep technical notebook: [notebooks/sanctum_deep_dive.ipynb](notebooks/sanctum_deep_dive.ipynb)
- OpenAPI YAML: [docs/openapi/security_capabilities_openapi.yaml](docs/openapi/security_capabilities_openapi.yaml)
- OpenAPI JSON: [docs/openapi/security_capabilities_openapi.json](docs/openapi/security_capabilities_openapi.json)
- FastAPI export: [docs/openapi/openapi.json](docs/openapi/openapi.json)
- Adapter contracts: [src/sanctum_suite/core/security_capability_adapters.py](src/sanctum_suite/core/security_capability_adapters.py)
- Safe SDK examples: [src/sanctum_suite/core/security_capability_sdk_examples.py](src/sanctum_suite/core/security_capability_sdk_examples.py)

## Operational stance

This repository is designed as a reviewable, architecture-oriented platform. It is not presented as a live production-connected deployment. The default posture is explicit operator configuration and evidence-based review before any real-world source is treated as trusted.

## Implementation waves

The current implementation follows a live-ready phased model rather than a blanket claim of production connectivity. The immediate wave is the second operational layer: BAM, HIRS, paccor, RIM-Tool, ELK, and Terraform. This group is treated as a real integration train with explicit API, authentication, and evidence contracts, while remaining fail-closed until environment credentials and runtime access are present.

The next expansion continues in the same pattern:

- Legacy host baselines: HP-UX, Oracle Solaris, OpenVMS
- Embedded control-plane: VxWorks
- AI/graph and autonomous orchestration: GNN, Agentic AI, Sec-PaLM, Palantir Gotham / Foundry
- Key-distribution and hardware assurance: QKD, Intel Loihi, IBM TrueNorth
- Long-tail evidence and archival: DNA Data Storage, retention policy, audit review

This sequencing preserves the distinction between adapter-only shells and live-ready operational contracts while ensuring every listed capability is represented in the registry and the live-ready model. The architecture remains grounded in real sources, auth boundaries, and normalized event handling rather than treating unconfigured systems as already connected.

## Wave 2 implementation package

The current repository also includes a concrete operational backlog for the next complete wave, with explicit capability IDs, env vars, auth model, payloads, and health-check endpoints for the legacy, embedded, AI, quantum, and neuromorphic groups.

See: [docs/PHASE_2_LIVE_READY_WAVE.md](docs/PHASE_2_LIVE_READY_WAVE.md)

## Wave 3 implementation package

The next complete deployment wave adds the remaining host, embedded, AI, and hardware assurance modules in the same live-ready pattern:

- legacy host baselines
- embedded control-plane (VxWorks)
- graph / GNN analytics
- agentic AI
- QKD key distribution
- neuromorphic compute

See: [docs/PHASE_3_LIVE_READY_WAVE.md](docs/PHASE_3_LIVE_READY_WAVE.md)

## Wave 4 implementation package

The subsequent live-ready wave extends the model to mission, signals, long-tail retention, and governance intelligence:

- signals intelligence (XKeyscore)
- collection intelligence (Boundless Informant)
- mission integration (US-984XN / PRISM)
- long-term archival storage
- AI governance and graph fusion

See: [docs/PHASE_4_LIVE_READY_WAVE.md](docs/PHASE_4_LIVE_READY_WAVE.md)

## Wave 5 implementation package

The final intelligence and governance wave completes the live-ready rollout for mission, collection, archive retention, AI governance, and data fusion:

- XKeyscore / signals intelligence
- Boundless Informant / collection intelligence
- US-984XN / PRISM mission integration
- DNA Data Storage / long-term retention
- Sec-PaLM / AI governance
- Palantir Gotham / Foundry / graph data fusion

See: [docs/PHASE_5_LIVE_READY_WAVE.md](docs/PHASE_5_LIVE_READY_WAVE.md)

## License

See the full project license here: [LICENSE](LICENSE).

## View-only notice

This repository is provided for review, evaluation, and architecture inspection only. It is not authorized for execution, deployment, redistribution, or operational use without separate approval.
