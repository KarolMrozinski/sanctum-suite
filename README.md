<div align="center">

# SANCTUM SUITE

</div>

<div align="center">
  <img src="https://img.shields.io/badge/Next.js-16.4.2-000000?style=for-the-badge&logo=next.js&logoColor=white" alt="Next.js 16.4.2" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=white" alt="React 19" />
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript 5" />
  <img src="https://img.shields.io/badge/Tailwind-4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind CSS 4" />
  <img src="https://img.shields.io/badge/Node.js-20+-339933?style=for-the-badge&logo=node.js&logoColor=white" alt="Node.js" />
  <img src="https://img.shields.io/badge/npm-10+-CB3837?style=for-the-badge&logo=npm&logoColor=white" alt="npm" />
  <img src="https://img.shields.io/badge/C%23-9.0-239120?style=for-the-badge&logo=csharp&logoColor=white" alt="C#" />
  <img src="https://img.shields.io/badge/WPF-.NET-512BD4?style=for-the-badge&logo=.net&logoColor=white" alt="WPF" />
  <img src="https://img.shields.io/badge/PowerShell-7-5391FE?style=for-the-badge&logo=powershell&logoColor=white" alt="PowerShell" />
  <img src="https://img.shields.io/badge/Python-3-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Rust-1.80+-000000?style=for-the-badge&logo=rust&logoColor=white" alt="Rust" />
  <img src="https://img.shields.io/badge/Ada-GNAT-00A9CE?style=for-the-badge&logo=ada&logoColor=white" alt="Ada" />
</div>

## Repository overview

Sanctum Suite is a premium cyber threat-intelligence workspace built around an OpenCTI-inspired analyst experience and branded as Sanctum Suite. The repository combines a live-like CTI dashboard, a native desktop launcher flow, and a modular security ecosystem for local operations, documentation, integrations, and deployment readiness.

The product currently focuses on:

- executive and operational overview panels
- adversary and campaign threat analysis
- entity, asset, and identity tracking
- investigations and workflow tracking
- alert feed and incident severity monitoring
- native-like Windows startup behavior for desktop-style use

## Premium repo layout

This repository follows a premium, product-oriented structure for quick navigation and future growth:

```text
app/           # product application and core runtime
desktop/       # desktop shell, launcher package, and native wrappers
integrations/  # references, connectors, and external integrations
security/      # security posture, audit flow, and policy docs
resources/     # branding, UI assets, icons, and supporting files
docs/          # product docs, notes, notebooks, and references
build/         # build, packaging, and release-oriented assets
reports/       # generated reports, audits, summaries, and exports
```

Legacy support files remain in the root for compatibility while the premium structure above is the canonical working map.

## Status

The application is working as a local dashboard product with realistic CTI mock data and a hardened launcher flow. The runtime serves successfully on `http://localhost:3000`, and the project is deliberately shaped to behave like a desktop product without losing the direct browser-driven development flow.

## Technology stack

| Layer | Stack |
|---|---|
| Frontend | Next.js + React + TypeScript |
| Styling | Tailwind CSS + glassmorphism + cyber UI |
| Runtime | Node.js + npm + local dev server |
| Desktop wrapper | .NET + C# + WPF + Windows launcher flow |
| Automation | PowerShell + CMD + BAT launcher scripts |
| Security model | Python + Rust + Ada + APL + HALS |

## Run locally

```bash
cd sanctum-dashboard
npm install
npm run dev
```

Open:

- `http://localhost:3000`

Optional Windows launcher entrypoints:

- `start-sanctum-suite.cmd`
- `run-sanctum-suite.bat`
- `sanctum-suite-gui-launcher.ps1`
- `SanctumSuiteLauncher.exe`

These entrypoints are built to avoid duplicate launches and preserve a single-instance desktop-like workflow.

## Core product sections

### Overview
Executive-level snapshot of security posture, operational visibility, and response readiness.

### Threats
Adversary campaigns, indicators, attack surfaces, and evolving risk posture.

### Entities
Hosts, identities, assets, and stakeholder context tied to investigations.

### Investigations
Timeline tracking, analyst workflows, and operational case handling.

### Alerts
Live incident feed, priority triage, and operator response states.

## Design language

Sanctum Suite takes a premium cyber-ops direction:

- deep navy and graphite interface base
- cyan/teal glow accents and glass panels
- dense analyst workbench layout
- strong hierarchy and premium minimal chrome
- high-signal data surfaces for real operational work

## Documentation and references

- [INDEX.md](INDEX.md)
- [sanctum-dashboard/README.md](sanctum-dashboard/README.md)
- [security/SECURITY.md](security/SECURITY.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [docs](docs)
- [notebooks/sanctum_deep_dive.ipynb](notebooks/sanctum_deep_dive.ipynb)

## Notes

The repository is a hybrid product: a polished local web application with desktop-shell behavior and security-oriented engineering infrastructure. It is built for local execution, operator review, and future deployment readiness.

## License

See [LICENSE](LICENSE).
