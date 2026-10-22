<div align="center">

# SANCTUM-SUITE

### Trust-aware security engineering for controlled environments

**Verify · Attest · Audit**

CLI, API, telemetry workflows, and governance tooling for supply-chain verification, operational assurance, and policy-driven security review.

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Next.js-dashboard-111827?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js dashboard">
  <img src="https://img.shields.io/badge/status-beta-f59e0b?style=flat-square" alt="Beta status">
  <img src="https://img.shields.io/badge/version-6.0.0-2563eb?style=flat-square" alt="Version 6.0.0">
</p>

</div>

## Overview

SANCTUM-SUITE is a modular security engineering platform designed for environments where trust, evidence, and explicit authorization matter as much as tooling itself. It brings together security workflows, attestation patterns, telemetry correlation, policy enforcement, and reporting into a single operational framework.

The project is intended for controlled, auditable, and security-conscious deployments where operators need stronger visibility into what was checked, why it was allowed, and what evidence supports the decision.

## Why SANCTUM-SUITE?

Modern security programs often fail not because the right tools are missing, but because the environment lacks clear evidence, policy boundaries, and verifiable trust context. SANCTUM-SUITE addresses that gap by combining:

- policy-aware audit workflows
- attestation and trust verification hooks
- telemetry ingestion and event correlation
- supply-chain and artifact verification flows
- structured reporting for operators and auditors
- optional CLI, API, and dashboard interfaces

## Core capabilities

- 🔐 Supply chain verification: Sigstore/Cosign-style attestations, policy checks, SBOM-oriented reporting
- 🧾 Executive reporting: structured JSON and Markdown outputs for technical and governance audiences
- 🛡️ Trust and attestation: TPM/Measured Boot awareness, policy enforcement, and attestation gates
- 📦 Air-gap readiness: local execution patterns, evidence handling, and offline-first operational design
- 🔭 Telemetry and auditability: Parquet/Arrow ingestion, event correlation, incident traceability
- 🧪 AI safety and privacy experiments: prompt-risk evaluation, secure flow patterns, controlled research tooling

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
sanctum --help
```

Optional dashboard:

```bash
cd sanctum-dashboard
npm install
npm run dev
```

## Project structure

```text
.
├── src/                  # Core Python package and security logic
├── notebooks/            # Deep-dive technical and architectural notes
├── docs/                 # Installation and operational guidance
├── policies/             # OPA policy definitions
├── sanctum-dashboard/    # Optional Next.js dashboard
├── scripts/              # Helper tooling and automation scripts
├── README.md             # Project overview
├── DEPLOYMENT.md         # Deployment runbook
├── SECURITY.md           # Security guidance and controls
├── LICENSE               # Source-available licensing terms
├── pyproject.toml        # Packaging and dependency metadata
├── action.yml            # GitHub Action metadata
└── .github/              # CI and repository automation
```

## Main modules

- Active audit and policy-driven verification
- Incident response and access-audit workflows
- AI safety and prompt-analysis experiments
- CLI, REST API, and dashboard interfaces
- Trust attestation and enforcement controls
- Privacy-focused and experimental security research components

## Documentation

- [Deep dive notebook](./notebooks/sanctum_deep_dive.ipynb)
- [Deployment guide](./DEPLOYMENT.md)
- [Security policy](./SECURITY.md)
- [License](./LICENSE)

## Project status

> SANCTUM-SUITE is currently in beta. Some modules may be experimental, partially integrated, or intended for controlled evaluation environments rather than broad production deployment.

This repository is designed for secure evaluation, governed operations, and research-oriented security workflows. It does not replace formal certification, external attestation, or independent validation for production environments.

## Recommended reading

- Start with this README for the high-level overview
- Read the [deep-dive notebook](./notebooks/sanctum_deep_dive.ipynb) for architecture and rationale
- Review [DEPLOYMENT.md](./DEPLOYMENT.md) for operational setup and environment guidance
- Review [SECURITY.md](./SECURITY.md) for project safeguards and security posture

## License

SANCTUM-SUITE is distributed under a limited source-available license. Please review the full terms in [LICENSE](./LICENSE) before using, deploying, or adapting the project.

