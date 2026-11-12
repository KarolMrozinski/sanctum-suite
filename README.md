<div align="center">

# SANCTUM SUITE

<p>
  <img src="https://img.shields.io/badge/Next.js-16.4.2-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js 16.4.2" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=white" alt="React 19" />
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript 5" />
  <img src="https://img.shields.io/badge/Tailwind-4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind CSS 4" />
  <img src="https://img.shields.io/badge/Node.js-20+-339933?style=for-the-badge&logo=node.js&logoColor=white" alt="Node.js" />
  <img src="https://img.shields.io/badge/C%23-9.0-239120?style=for-the-badge&logo=csharp&logoColor=white" alt="C#" />
  <img src="https://img.shields.io/badge/WPF-.NET-512BD4?style=for-the-badge&logo=.net&logoColor=white" alt="WPF" />
  <img src="https://img.shields.io/badge/PowerShell-7-5391FE?style=for-the-badge&logo=powershell&logoColor=white" alt="PowerShell" />
</p>

<p>
  <a href="http://localhost:3000"><img src="https://img.shields.io/badge/Launch%20Dashboard-Open-00E5FF?style=for-the-badge" alt="Launch Dashboard" /></a>
  <a href="INDEX.md"><img src="https://img.shields.io/badge/Repo%20Index-Open-7C3AED?style=for-the-badge" alt="Repo Index" /></a>
  <a href="docs/README.md"><img src="https://img.shields.io/badge/Docs-Open-94A3B8?style=for-the-badge" alt="Docs" /></a>
</p>

</div>

## Final release hero

Sanctum Suite is a premium cyber threat-intelligence platform designed for modern security operations teams. Built around a dark, analyst-first experience, the project blends a polished OpenCTI-style dashboard, desktop-native launcher behavior, and modular product architecture into a single cohesive security workspace.

## Product overview

Sanctum Suite is structured as a high-end local-first CTI environment with a clear operational flow across intelligence, investigation, and response-oriented views. It combines the visual language of a modern security operations console with practical UX patterns suited for demos, internal review, and future deployment to an external environment.

### What’s inside

- OpenCTI-inspired analyst dashboard with threat intelligence workflow
- Structured views for overview, threats, entities, investigations, and alerts
- Premium dark-glass UI with crisp hierarchy and active monitoring cues
- Local-first runtime with desktop launcher flow for Windows users
- Modular repo layout prepared for future integrations and real data sources

### Core capabilities

- Threat-centric intelligence overview
- Entity relationship and context views
- Investigation tracking and analyst workflow support
- Alert monitoring and live-style operational summaries
- Desktop launch shell with URL-aware runtime targeting
- Clean product architecture and documentation-first repo organization

## Quick start

### 1. Run the dashboard locally

```bash
cd sanctum-dashboard
npm install
npm run dev
```

Then open:

- `http://localhost:3000`

### 2. Launch the desktop wrapper

From the repository root, use one of the supported entrypoints:

- `start-sanctum-suite.cmd`
- `run-sanctum-suite.bat`
- `sanctum-suite-gui-launcher.ps1`
- `SanctumSuiteLauncher.exe`

### 3. Stop or reset the runtime

```bash
stop-sanctum-suite.cmd
```

This keeps the lifecycle clean and prevents duplicate process or browser reopen loops.

### 4. Explore the main product sections

- Overview
- Threats
- Entities
- Investigations
- Alerts

## Root-level naming standard

The repository is organized around a clean product-first naming model:

```text
README.md          primary product landing page
INDEX.md           repository overview and navigation entrypoint
docs/              documentation and operational references
app/               application layer and system runtime logic
desktop/           desktop shell and native launcher package
integrations/      integration references and external system hooks
security/          security posture, guidance, and hardening docs
resources/         brand assets, visuals, and supporting resources
build/             packaging and release-oriented build artifacts
reports/           operational summaries and report exports
```

Legacy support files remain available for compatibility, while the structure above represents the final product-facing standard.

## Repository layout

```text
app/           Product runtime and application logic
desktop/       Desktop launcher and Windows app wrapper
integrations/  External integrations, references, and system hooks
security/      Security documentation and governance
resources/     Brand assets and design resources
docs/          Documentation, runbooks, and product notes
build/         Packaging, build, and deployment scaffolding
reports/       Generated reports and operational exports
```

## Technology stack

| Layer | Stack |
|---|---|
| Frontend | Next.js + React + TypeScript |
| Styling | Tailwind CSS + glassmorphism + cyber UI |
| Runtime | Node.js + npm + local development server |
| Desktop wrapper | .NET + C# + WPF + Windows launcher flow |
| Automation | PowerShell + CMD + BAT startup scripts |
| Security model | Python + Rust + future security tooling layers |

## Documentation and navigation

- [INDEX.md](INDEX.md)
- [sanctum-dashboard/README.md](sanctum-dashboard/README.md)
- [docs/README.md](docs/README.md)
- [security/SECURITY.md](security/SECURITY.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [CHANGELOG.md](CHANGELOG.md)
- [LICENSE](LICENSE)

## Design language

Sanctum Suite follows a premium cyber-operations visual system built around:

- deep navy and graphite surfaces
- cyan and teal signal accents
- glass-effect panels with soft glow
- dense, analyst-first workspace layout
- minimal premium chrome for a desktop-native feel

## Current status

The project currently sits in a polished local-first operational prototype phase: the CTI interface is fully styled and functional, the desktop launcher layer is substantially improved, and the repo is organized around a more product-ready structure. It is ready for local demos, validation, and future expansion into external deployment or live backend integration.

## License

See [LICENSE](LICENSE).
