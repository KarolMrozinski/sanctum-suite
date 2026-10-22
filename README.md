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
    <td><a href="#security-capability-model"><strong>Security capability model</strong></a><br/>Normalized mapping from technologies to evidence-backed security functions.</td>
    <td><a href="#api-contract"><strong>API contract</strong></a><br/>REST endpoints for capability discovery, evidence exchange, and controlled sync.</td>
  </tr>
  <tr>
    <td><a href="#documentation"><strong>Documentation</strong></a><br/>Detailed notebook, OpenAPI contracts, and adapter examples for future integration.</td>
    <td><a href="#product-overview"><strong>Product overview</strong></a><br/>Explicit evidence-based review and operator-controlled trust boundaries before live integration.</td>
  </tr>
</table>

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

## Documentation

- Deep technical notebook: [notebooks/sanctum_deep_dive.ipynb](notebooks/sanctum_deep_dive.ipynb)
- OpenAPI YAML: [docs/openapi/security_capabilities_openapi.yaml](docs/openapi/security_capabilities_openapi.yaml)
- OpenAPI JSON: [docs/openapi/security_capabilities_openapi.json](docs/openapi/security_capabilities_openapi.json)
- FastAPI export: [docs/openapi/openapi.json](docs/openapi/openapi.json)
- Adapter contracts: [src/sanctum_suite/core/security_capability_adapters.py](src/sanctum_suite/core/security_capability_adapters.py)
- Safe SDK examples: [src/sanctum_suite/core/security_capability_sdk_examples.py](src/sanctum_suite/core/security_capability_sdk_examples.py)

## Product overview

SANCTUM-SUITE is a reviewable security capability framework for mapping technology stacks, trust boundaries, and evidence-backed security functions into a normalized architecture model. It is designed to help organizations reason about what is operationally verified, what is only planned, and what remains unconfigured before live integration is considered.

The platform is intentionally conservative: capability adapters do not claim real operational status without explicit runtime context, credentials, policy approval, and evidence. This keeps the model grounded in actual deployment reality rather than marketing claims or broad tool inventories.

## License

See the full project license here: [LICENSE](LICENSE).

## View-only notice

This repository is provided for review, evaluation, and architecture inspection only. It is not authorized for execution, deployment, redistribution, or operational use without separate approval.
