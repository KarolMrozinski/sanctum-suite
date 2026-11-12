# Compliance Policy

## Purpose

This document describes a practical compliance posture that aligns the SANCTUM-SUITE planning model with common security and supply-chain requirements for product, infrastructure, and audit review. The repository intentionally keeps cloud and runtime actions in a `PLAN_ONLY` mode and therefore this policy is guidance for review, governance, and release control rather than a live enforcement engine.

## Compliance domains mapped to the project model

### ISO 27001

The project supports the following control themes:

- information security policies and ownership
- asset and component inventory through SBOM review
- access control and identity verification
- incident handling and operational evidence
- secure software development and release governance
- continuous monitoring and review processing

Recommended evidence:

- signed release artifacts
- attestation/provenance records
- CVE mapping and risk review
- runtime policy documentation
- approval records for exceptions and promotions

### SOC 2

The project aligns with the core operational principle of demonstrating that security responsibilities are defined, monitored, and evidenced.

Relevant control areas:

- logical and physical access control
- change management and release governance
- system monitoring and evidence review
- vendor and supply-chain risk management
- incident and exception handling

Recommended evidence:

- release checklist records
- SBOM and vulnerability review history
- approval audit trail for security/compliance sign-off
- runtime policy and workload risk register

### NIS2

This framework places strong emphasis on operational resilience, governance, and trustworthy digital supply chains. The project supports this by modeling:

- risk-based release approval
- supply-chain verification
- secure configuration review
- runtime and workload awareness for critical services
- structured evidence for security operations and business continuity

Recommended evidence:

- provenance and attestation logs
- signed release artifacts
- CVE and dependency review outputs
- approved network and workload control model

### CRA (Cyber Resilience Act)

The CRA requires digital products to be resilient throughout their lifecycle, with clear evidence of controlled development and risk handling.

The project supports this by encouraging:

- secure release process
- software bill of materials and dependency analysis
- vulnerability review and exception handling
- runtime policy alignment for workloads and containers
- explicit ownership and approval of security changes

Recommended evidence:

- release policy checklist
- SBOM generation and retention
- vulnerability review and accepted exceptions
- implementation and runtime profile documentation

## Control expectations for release governance

The release process should require the following before production promotion:

1. artifact signed and verified
2. identity and issuer validated
3. provenance and attestation reviewed
4. SBOM generated and reviewed
5. vulnerabilities mapped and exceptions documented
6. workload profile checked against Falco/runtime controls
7. compliance/security approval recorded

## Exception handling

Exceptions must be:

- time-bound
- assigned to a named owner
- reviewed against business and security risk
- supported by compensating controls
- recorded in the release evidence trail

## Minimum evidence pack for an internal audit

The minimum internal evidence set should include:

- source revision and build metadata
- signed release artifact and verification log
- SBOM in selected format (CycloneDX and/or SPDX)
- vulnerability scan / CVE mapping summary
- runtime control review for deployed workloads
- release approval and exception log

## Conclusion

This repository is a planning and review model rather than a live enforcement platform. It is best used as a governance layer: it documents the control logic, the evidence trail, and the decision gates required for regulated, security-conscious software delivery.
