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
    <td><a href="#operational-stance"><strong>Operational stance</strong></a><br/>Explicit evidence-based review and operator-controlled trust boundaries before live integration.</td>
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

The current implementation follows a live-ready phased model rather than a blanket claim of production connectivity. The first operational activation sequence is: GCP, ELK, Terraform, and Kafka. Only after the environment supplies real project IDs, endpoint URLs, API keys, RBAC, and health validation do these adapters move from `NOT_CONFIGURED` to `READY`.

Operational readiness is now evaluated through the wave-status API, which checks the required env vars and auth model for each phase before reporting `READY`.

- `GET /api/v1/security-capabilities/waves`
- `GET /api/v1/security-capabilities/waves/{wave_name}`
- `GET /api/v1/security-capabilities/waves/{wave_name}/status`

The second operational wave is: BAM, HIRS, paccor, and RIM-Tool. It follows the same fail-closed pattern: real API access and signed policy context are required before the capability is treated as live.

The next expansion continues in the same pattern:

- Legacy host baselines: HP-UX, Oracle Solaris, OpenVMS
- Embedded control-plane: VxWorks
- AI/graph and autonomous orchestration: GNN, Agentic AI, Sec-PaLM, Palantir Gotham / Foundry
- Key-distribution and hardware assurance: QKD, Intel Loihi, IBM TrueNorth
- Long-tail evidence and archival: DNA Data Storage, retention policy, audit review

This sequencing preserves the distinction between adapter-only shells and live-ready operational contracts while ensuring every listed capability is represented in the registry and the live-ready model. The architecture remains grounded in real sources, auth boundaries, and normalized event handling rather than treating unconfigured systems as already connected.

## Wave 1 implementation package

The first live-ready operational wave focuses on the realistic, high-value control plane for platform telemetry and evidence flow:

- Google Cloud Platform (GCP)
- Elasticsearch / Logstash / Kibana (ELK)
- HashiCorp Terraform
- Kafka event bus

See: [docs/PHASE_1_LIVE_READY_WAVE.md](docs/PHASE_1_LIVE_READY_WAVE.md)

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

## Operational deployment assets

The repository now includes concrete deployment artifacts for real Kubernetes rollouts, organized under the dedicated deployment folder:

- Deployment instruction index: [deployment/README.md](deployment/README.md)
- Azure AKS deployment checklist: [deployment/azure-aks/deployment-checklist.md](deployment/azure-aks/deployment-checklist.md)
- GCP GKE deployment checklist: [deployment/gcp-gke/deployment-checklist.md](deployment/gcp-gke/deployment-checklist.md)
- Secret manager guidance for Vault / GCP Secret Manager / Azure Key Vault: [deployment/secret-managers/README.md](deployment/secret-managers/README.md)
- Phase 1 rollout checklist: [deployment/phase1/phase1-rollout-checklist.md](deployment/phase1/phase1-rollout-checklist.md)
- Example Phase 1 environment file for GCP: [.env.phase1.gcp.example](.env.phase1.gcp.example)
- Example Phase 1 environment file for Azure AKS: [.env.phase1.aks.example](.env.phase1.aks.example)
- GitOps ApplicationSet for a production GKE cluster: [argocd/applicationset-gke-prod.yaml](argocd/applicationset-gke-prod.yaml)
- GitOps ApplicationSet for a production AKS cluster: [argocd/applicationset-aks-prod.yaml](argocd/applicationset-aks-prod.yaml)
- Full Azure AKS Phase 1 deployment manifest: [k8s/phase1-live-ready-aks.yaml](k8s/phase1-live-ready-aks.yaml)
- Phase-by-phase deployment plan with real namespace and service account names: [docs/DEPLOY_PHASE_BY_PHASE.md](docs/DEPLOY_PHASE_BY_PHASE.md)
- Step-by-step Azure AKS cluster commands: [docs/CLUSTER_COMMANDS_PHASE1_AKS.md](docs/CLUSTER_COMMANDS_PHASE1_AKS.md)

## License

See the full project license here: [LICENSE](LICENSE).

## View-only notice

This repository is provided for review, evaluation, and architecture inspection only. It is not authorized for execution, deployment, redistribution, or operational use without separate approval.
