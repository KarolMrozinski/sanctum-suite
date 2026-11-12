# Sanctum Suite — Repository Index

<div align="center">

# SANCTUM SUITE

</div>

## Overview

Sanctum Suite is a premium cyber threat-intelligence workspace built around a dark OpenCTI-inspired analyst experience and rebranded into the Sanctum Suite identity. The project combines a live-like dashboard, operational CTI sections, desktop-style launch flow, and modular infrastructure for future real-world deployment.

## Repository map

```text
app/                 Product application and runtime logic
desktop/             Desktop shell and Windows launcher resources
integrations/        External references, connectors, and integration layers
security/            Security documentation, audits, policy references
resources/           Brand assets, icons, visual resources, and support files
docs/                Documentation, notes, notebooks, and repo guidance
build/               Build, packaging, and release-oriented utilities
reports/             Generated reports, outputs, and audit summaries
```

## Key project areas

### Application layer
- [app](app)
- [sanctum-dashboard](sanctum-dashboard)
- [sanctum-dashboard/README.md](sanctum-dashboard/README.md)

### Desktop launcher layer
- [desktop](desktop)
- [start-sanctum-suite.cmd](start-sanctum-suite.cmd)
- [stop-sanctum-suite.cmd](stop-sanctum-suite.cmd)
- [run-sanctum-suite.bat](run-sanctum-suite.bat)
- [sanctum-suite-gui-launcher.ps1](sanctum-suite-gui-launcher.ps1)

### Integration and security layer
- [integrations](integrations)
- [security](security)
- [security/SECURITY.md](security/SECURITY.md)

### Documentation and resources
- [docs](docs)
- [resources](resources)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [CHANGELOG.md](CHANGELOG.md)
- [LICENSE](LICENSE)

## Product focus

- Threat intelligence workspace
- Analyst-first dashboard UX
- Live-like data sections: Overview, Threats, Entities, Investigations, Alerts
- Desktop-mode startup and single-instance behavior
- Local-first workflow with future external URL readiness

## Local run

```bash
cd sanctum-dashboard
npm install
npm run dev
```

Then open:

- http://localhost:3000

## Notes

This root index is the entry point for the repository and reflects the premium structure of the project without removing legacy compatibility files.
