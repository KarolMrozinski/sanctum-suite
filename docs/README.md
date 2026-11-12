# Sanctum Suite Documentation

<div align="center">

# DOCUMENTATION

<p>
  <a href="../README.md"><img src="https://img.shields.io/badge/Main%20Repo-Open-00E5FF?style=for-the-badge" alt="Main Repo" /></a>
  <a href="../INDEX.md"><img src="https://img.shields.io/badge/Index-Open-7C3AED?style=for-the-badge" alt="Index" /></a>
</p>

</div>

## Overview

This documentation hub captures the final product direction of Sanctum Suite: a premium cyber operations workspace with a native-like desktop launcher, a live CTI dashboard, and a local-first runtime model designed for professional demos and future deployment expansion.

## Finalized scope

### Product and experience
- premium OpenCTI-inspired CTI dashboard with analyst-first workflow
- dark cyber styling with glass surfaces, glow accents, and operational hierarchy
- live-like operational sections: Overview, Threats, Entities, Investigations, Alerts
- desktop launcher flow designed to feel closer to a native Windows app than a browser wrapper

### Runtime and launcher
- local dev startup via `sanctum-dashboard`
- root-level launcher scripts for start/stop/open flow
- single-instance and stale-state protection for clean desktop behavior
- URL-configurable app target with localhost fallback for future external deployment

### Repository structure
- premium repo organization aligned to product layering
- clear separation between app, desktop, integrations, security, resources, docs, build, and reports
- consistent naming and root-level navigation for easier onboarding

## Documentation map

```text
docs/
  README.md
  INSTALLATION.md
  DEPLOYMENT_CHECKLIST_AKS.md
  DEPLOYMENT_CHECKLIST_GCP_AZURE_K8S.md
  DEPLOY_PHASE_BY_PHASE.md
  PRODUCTION_RUNBOOK_ALL_PHASES.md
  RELEASE_CHECKLIST.md
  TELEMETRY_PIPELINE.md
  notebooks/
  openapi/
```

## Primary references

- [README.md](../README.md)
- [INDEX.md](../INDEX.md)
- [INSTALLATION.md](INSTALLATION.md)
- [DEPLOYMENT.md](../DEPLOYMENT.md)
- [security/SECURITY.md](../security/SECURITY.md)
- [notebooks](notebooks)
- [openapi](openapi)

## Launch and runtime flow

### Local app

```bash
cd sanctum-dashboard
npm install
npm run dev
```

Open:

- `http://localhost:3000`

### Desktop launcher

From the repository root:

- `start-sanctum-suite.cmd`
- `run-sanctum-suite.bat`
- `sanctum-suite-gui-launcher.ps1`
- `SanctumSuiteLauncher.exe`

Use `stop-sanctum-suite.cmd` to shut down the managed runtime and clear stale state.

## Mission

The documentation layer exists to help operators, developers, and security teams understand how Sanctum Suite runs locally, how the desktop launcher behaves, and how the project can expand into a stronger production-ready operating model without losing its product identity.

## Notes

This documentation remains aligned with the current local-first architecture while preserving room for future real-environment integration, deployment hardening, and broader product maturity.
