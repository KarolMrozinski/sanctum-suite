# Changelog

All notable changes to SANCTUM-SUITE are documented in this file.

## [6.0.0] - 2026-10-18

### Added
- Python package entrypoint via `sanctum` CLI.
- CLI commands for audit orchestration, analytics, dashboard and port scanning.
- Packaging and distribution validation for editable install and built wheel/sdist artifacts.
- Marketing, About, Features, Documentation, Pricing, Privacy, and Workbench dashboard routes.
- Lead inquiry form with server-side webhook forwarding and validation.
- Installation, release overview, security, and monetization documentation; PDF release overview.
- AWS deployment runbook and standalone dashboard container build.

### Changed
- Stabilized Console/Rich output on Windows to prevent Unicode encoding crashes during CLI and TUI use.
- Normalized default help and status text for terminal compatibility.
- Separated the marketing site from the operational workbench and removed fabricated live graph data.
- Added product and pricing caveats that distinguish draft commercial options from active offers.
- Restricted API deployment to configured strong credentials and bound the Compose port to localhost.
- Made the automated audit workflow manual and require explicit authorization confirmation.

### Fixed
- Unicode encoding issues affecting `--help` and TUI rendering on legacy Windows terminals.
- CLI output compatibility across Python and shell environments.
- Restored access to the operational dashboard at `/workbench`.
- Removed hard-coded API credentials, fake incident telemetry, and fixed demo metrics.

### Security
- Added release security policy and vulnerability reporting workflow.
- Documented operational handling for security disclosure and triage.
