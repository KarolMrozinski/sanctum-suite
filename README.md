<div align="center">

# SANCTUM-SUITE

</div>

<div align="center">

### Trust-aware security engineering for controlled environments

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/FastAPI-API-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Status-beta-f59e0b?style=flat-square" alt="Beta" />
  <img src="https://img.shields.io/badge/Docs-OpenAPI-2563eb?style=flat-square" alt="OpenAPI" />
</p>

</div>

## Why was created ?

Modern security programs often fail not because the right tools are missing, but because the environment lacks grounded evidence, clear trust boundaries, and explicit operator intent. SANCTUM-SUITE was created to give organizations a structured way to define what is being verified, what evidence exists, and what remains untrusted or unconfigured before live integration is considered.

## Core pillars

<table>
  <tr>
    <td><a href="#platform-catalog"><strong>Platform catalog</strong></a><br/>Structured inventory of technologies and security domains.</td>
    <td><a href="#security-capability-model"><strong>Security capability model</strong></a><br/>Normalized mapping from technologies to evidence-backed capabilities.</td>
  </tr>
  <tr>
    <td><a href="#api-contract"><strong>API contract</strong></a><br/>REST endpoints for capability discovery and evidence exchange.</td>
    <td><a href="#documentation"><strong>Documentation</strong></a><br/>Deep technical notebook, OpenAPI schema, and adapter examples.</td>
  </tr>
</table>

## Platform catalog

The project maintains a structured catalog of operator-managed technology surfaces that may later be bound to real evidence sources.

- Binary analysis and reversing: Ghidra, BAM, HIRS, paccor, RIM-Tool
- OS and runtime integrity: HP-UX, Oracle Solaris, OpenVMS, SELinux, VxWorks
- Monitoring and intelligence: GRASSMARLIN, ELITEWOLF, WALKOFF, PRISM, XKeyscore, Boundless Informant
- Cloud and infrastructure: C2S, JWCC, Mandiant Advantage, Mandiant Automated Defense, Google Cloud Platform (GCP)
- Software and data platforms: C/C++, Go, Assembly, Apache Accumulo, Hadoop, Spark, Kafka, ELK Stack, Terraform
- AI and emerging hardware: Sec-PaLM, Palantir Gotham / Foundry, QKD, Loihi, TrueNorth, GNN, Agentic AI, DNA Data Storage

This catalog is intentionally evidence-first: technologies are modeled as capability surfaces, not as guaranteed live integrations.

## Security capability model

SANCTUM-SUITE maps technologies to normalized security capabilities such as:

- `security-capability:binary-analysis`
- `security-capability:runtime-attestation`
- `security-capability:linux-integrity`
- `security-capability:gcp-platform`
- `security-capability:terraform-policy`
- `security-capability:observability`

Each capability includes:

- stable identifier
- source type
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

The implementation is intentionally safe by default and fail-closed when configuration or credentials are missing.

## Documentation

- Deep technical notebook: [notebooks/sanctum_deep_dive.ipynb](notebooks/sanctum_deep_dive.ipynb)
- OpenAPI YAML: [docs/openapi/security_capabilities_openapi.yaml](docs/openapi/security_capabilities_openapi.yaml)
- OpenAPI JSON: [docs/openapi/security_capabilities_openapi.json](docs/openapi/security_capabilities_openapi.json)
- FastAPI export: [docs/openapi/openapi.json](docs/openapi/openapi.json)
- Adapter contracts: [src/sanctum_suite/core/security_capability_adapters.py](src/sanctum_suite/core/security_capability_adapters.py)
- Safe SDK examples: [src/sanctum_suite/core/security_capability_sdk_examples.py](src/sanctum_suite/core/security_capability_sdk_examples.py)

## Operational stance

This repository is designed as a reviewable, architecture-oriented platform. It is not presented as a live, production-connected deployment. The default posture is explicit operator configuration and evidence-based review before any real-world data feed is treated as trusted.

## License

See the full project license here: [LICENSE](LICENSE).

## View-only notice

This repository is provided for review, evaluation, and architecture inspection only. It is not authorized for execution, deployment, redistribution, or operational use without separate approval.
