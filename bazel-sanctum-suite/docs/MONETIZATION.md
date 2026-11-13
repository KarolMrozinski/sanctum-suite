# Monetization Strategy

This is a planning document, not a commercial offer. The prices and packaging below are hypotheses for customer discovery; no checkout, billing, entitlement, or paid hosting service is implemented. Confirm rights with the copyright holder and complete legal review before offering paid access.

The current Python `CommercialLicenseManager` is not production licensing: it accepts tier prefixes without cryptographic verification and tracks usage only in process memory. Do not rely on it to enforce paid plans. A signed entitlement flow and durable, tenant-scoped metering must be designed and validated before subscriptions are offered.

## Recommended commercial model

SANCTUM-SUITE is best positioned as a dual-layer product:

1. Open-core / controlled-access foundation for technical validation and internal use.
2. Enterprise SaaS / private deployment layer for production customers.

This approach balances adoption and revenue while preserving licensing control over the platform's most sensitive capabilities.

## Pricing model

The owner indicated PLN as the preferred currency. No price, billing period, or payment processor has been approved. The following are possible packaging dimensions for discovery, not a published price list:

### Tier 1 — Developer / Evaluation
- Includes:
  - local CLI access
  - limited analytics workflows
  - offline report generation
  - community support

### Tier 2 — Team / SOC
- Includes:
  - multi-user access
  - central analytics dashboard
  - audit orchestration
  - team reports and export pipelines
  - prioritized support

### Tier 3 — Enterprise / Mission-Critical
- Price: custom quote
- Includes:
  - private deployment
  - dedicated onboarding
  - SLA and incident support
  - custom integrations
  - regulatory and governance support

## Revenue channels

- SaaS subscriptions for managed hosting and dashboards
- enterprise deployment licenses for private infrastructure
- annual support contracts
- custom compliance workshops and implementation services
- paid integration packages for Splunk, SIEM, EDR or custom SOC stack

## Packaging and distribution

- Python package distribution via wheel and sdist
- private or public GitHub release tags for versioned distribution
- optional Docker image for fast onboarding
- enterprise deployment package for secured environments

## Licensing guidance

The current repository license is a restricted source-available model. That is suitable for controlled commercial distribution, but it must be paired with a written commercial agreement for live production use, managed services, or deployed SaaS.

Recommended next step:

- define a customer-facing commercial agreement
- separate evaluation license from commercial use rights
- publish a standard terms sheet for enterprise sales

## Launch checklist

Before starting paid distribution:

- confirm legal ownership and commercial licensing terms
- finalize support SLAs
- publish pricing page and sales contact flow
- provide installation and operations documentation
- create onboarding guides and troubleshooting docs
- ensure billing and customer access workflow are in place
