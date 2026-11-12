<div align="center">

# SANCTUM SUITE

</div>

<div align="center">
  <p>
    <img src="https://img.shields.io/badge/Next.js-16.4.2-000000?style=flat-square&logo=next.js&logoColor=white" alt="Next.js 16.4.2" />
    <img src="https://img.shields.io/badge/Mode-Dashboard-0ea5e9?style=flat-square" alt="Dashboard mode" />
    <img src="https://img.shields.io/badge/Style-OpenCTI-inspired-111827?style=flat-square" alt="OpenCTI inspired" />
    <img src="https://img.shields.io/badge/Author-KarolMrozinski-22c55e?style=flat-square" alt="Author KarolMrozinski" />
  </p>
</div>

## Overview

Sanctum Suite is a premium cyber threat-intelligence workspace built as an OpenCTI-inspired dashboard and rebranded around the Sanctum Suite identity. The project combines a dark SOC/CTI aesthetic, glassmorphism panels, real operational sections, and a desktop-style launcher experience so the app feels closer to a native security workstation than a starter Next.js app.

The current implementation focuses on the live-like analyst experience:

- Overview with executive and operational KPIs
- Threats with adversary and campaign context
- Entities with affected systems, identities, and assets
- Investigations with timelines and status tracking
- Alerts with live feed and severity-based monitoring
- Desktop launcher flow for Windows startup, stop, reopen, and tray/minimize behavior

## Status

The project is now structured as a working local dashboard application with mock CTI data and a native-like launcher wrapper. The runtime serves successfully on `http://localhost:3000`, and the app is designed to behave like a desktop product without losing the browser-based development workflow.

## Run locally

```bash
cd sanctum-dashboard
npm install
npm run dev
```

Then open:

- `http://localhost:3000`

If the app is already running, the launcher will not restart it and will only open the browser once for the active session.

## Windows launcher

From the repo root, use the desktop-start scripts:

- `start-sanctum-suite.cmd`
- `run-sanctum-suite.bat`
- `SanctumSuiteLauncher.exe`
- `Sanctum Suite.lnk`

These entry points are intended to start the dashboard in a single-instance, desktop-like flow and prevent duplicate browser reopen loops while keeping the app stable and easy to manage.

## Product structure

```text
sanctum-dashboard/
  src/app/
  src/components/
  src/lib/
  public/
  package.json

root-level launchers/
  start-sanctum-suite.cmd
  stop-sanctum-suite.cmd
  run-sanctum-suite.bat
  sanctum-suite-gui-launcher.ps1
  SanctumSuiteLauncher/
  SanctumSuiteLauncher.exe
```

## Core sections

### Overview
Executive-level snapshot of security posture, attack surface coverage, operational visibility, and response readiness.

### Threats
Tracking of adversary campaigns, malware activity, indicators, and evolving risk posture.

### Entities
Inventory of impacted hosts, identities, assets, and stakeholders tied to investigations.

### Investigations
Workflows for case management, escalating response actions, and timeline-based analyst context.

### Alerts
Live feed of prioritized security incidents, severity states, and operator actions.

## Design language

Sanctum Suite deliberately preserves a premium cyber-ops feel:

- deep navy and graphite UI base
- cyan/teal glow accents and glass panels
- dense operational surfaces inspired by analyst workbenches
- clean data-rich cards with strong visual hierarchy
- minimal, premium chrome for desktop-shell behavior

## Notes

This repo combines an actual local web dashboard with Windows launcher artifacts for a more native desktop experience. It is designed for local execution and operator review rather than as a production-grade SOC backend.

## License

See [LICENSE](LICENSE).

## Documentation

- [notebooks/sanctum_deep_dive.ipynb](notebooks/sanctum_deep_dive.ipynb)
- [sanctum-dashboard/README.md](sanctum-dashboard/README.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [SECURITY.md](SECURITY.md)
