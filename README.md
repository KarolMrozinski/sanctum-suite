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

Sanctum Suite is a premium cyber threat-intelligence platform built to feel like a modern security operations desktop: dark, precise, glassy, and engineered for analyst flow. The project combines a high-end CTI dashboard, desktop-native Windows launch behavior, and modular architecture into one cohesive product experience.

## What’s inside

### Product experience
- OpenCTI-inspired cyber SOC dashboard
- Threats, entities, investigations, alerts, and overview workflows
- Premium dark glass UI with analyst-first hierarchy
- Local-first runtime with desktop launcher behavior for Windows

### Platform architecture
- Next.js + React + TypeScript frontend
- .NET + WPF desktop shell and launcher integration
- PowerShell/CMD entrypoints for single-instance startup
- Python, Rust, and security-oriented tooling layers for future expansion

### Operational model
- realistic mock CTI data for live-like analyst workflows
- local environment ready for review, testing, and demo use
- URL-ready design for future deployment and external hosting
- organized repo structure for product growth and maintenance

## How to use Sanctum Suite

### 1. Run the dashboard

```bash
cd sanctum-dashboard
npm install
npm run dev
```

Open the app:

- `http://localhost:3000`

### 2. Start the desktop launcher

From the repo root, use one of the supported launch entrypoints:

- `start-sanctum-suite.cmd`
- `run-sanctum-suite.bat`
- `sanctum-suite-gui-launcher.ps1`
- `SanctumSuiteLauncher.exe`

### 3. Stop or reset the runtime

Use the shutdown flow:

- `stop-sanctum-suite.cmd`

This keeps the launcher lifecycle clean and prevents duplicate browser reopen loops.

### 4. Use the product

Navigate through the main sections:

- Overview
- Threats
- Entities
- Investigations
- Alerts

## Root-level naming standard

The canonical root structure is organized around clarity and product-first naming:

```text
README.md          primary product landing page
INDEX.md           repository index and navigation entrypoint
docs/              documentation hub and operational references
app/               product runtime and UI code
desktop/           desktop launcher and Windows shell resources
integrations/      external integrations and references
security/          security documentation and hardening guidance
resources/         brand, visuals, and supporting assets
build/             packaging and release-oriented build assets
reports/           generated reports and operational exports
```

Legacy support files remain in the root for compatibility, but the names above are the final product-facing standard.

## Repository layout

```text
app/           Product application and runtime logic
desktop/       Desktop shell and launcher components
integrations/  Integrations, references, and external systems
security/      Security posture and governance documentation
resources/     Brand assets, visuals, and helper resources
docs/          Documentation, runbooks, and learning content
build/         Packaging, build, and deployment scaffolding
reports/       Audit summaries, reports, and exports
```

## Technology stack

| Layer | Stack |
|---|---|
| Frontend | Next.js + React + TypeScript |
| Styling | Tailwind CSS + glassmorphism + cyber UI |
| Runtime | Node.js + npm + local dev server |
| Desktop wrapper | .NET + C# + WPF + Windows launcher flow |
| Automation | PowerShell + CMD + BAT launch scripts |
| Security model | Python + Rust + Ada + APL + HALS |

## Documentation and navigation

- [INDEX.md](INDEX.md)
- [sanctum-dashboard/README.md](sanctum-dashboard/README.md)
- [docs/README.md](docs/README.md)
- [security/SECURITY.md](security/SECURITY.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [CHANGELOG.md](CHANGELOG.md)
- [LICENSE](LICENSE)

## Design language

Sanctum Suite intentionally uses a premium cyber-ops aesthetic:

- deep navy and graphite palette
- cyan/teal signal accents
- glass surfaces with soft glow
- dense analyst workspace layout
- minimal premium chrome for desktop-style feel

## Status

The project is currently in a local-first operational prototype phase with a polished CTI UX and a desktop launcher layer. It is ready for local use, review, demo, and future deployment expansion.

## License

See [LICENSE](LICENSE).
