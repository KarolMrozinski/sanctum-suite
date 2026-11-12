# Sanctum Suite Dashboard

A premium cyber operations dashboard inspired by OpenCTI and refined into the Sanctum Suite brand.

## What it includes

- OpenCTI-like threat intelligence layout
- Overview, threats, entities, investigations, and alerts sections
- Dark glassmorphism interface with cyber security styling
- Local mock data modeled around analyst workflows
- Desktop launcher integration for Windows startup and management

## Local run

```bash
cd sanctum-dashboard
npm install
npm run dev
```

Open:

- `http://localhost:3000`

## Build

```bash
npm run build
```

## App flow

The dashboard is structured around a live SOC/CTI operator experience:

- Overview: operational insights and exposure snapshot
- Threats: malicious campaign and actor context
- Entities: assets, identities, infrastructure, and impact mapping
- Investigations: timeline-driven casework and narrative progression
- Alerts: priority feed with severity and response posture

## Windows launcher

From the repository root:

- `start-sanctum-suite.cmd`
- `run-sanctum-suite.bat`
- `SanctumSuiteLauncher.exe`
- `Sanctum Suite.lnk`

These entry points are intended to start the dashboard in a desktop-like native workflow and keep the browser launch single-instance and stable.

## Notes

This app is designed as a polished local CTI dashboard and desktop wrapper. The data is intentionally realistic but local/mock-driven rather than a full production backend.
