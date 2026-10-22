# Security Review

## Scope

This document summarizes the repository-level security approach for the SANCTUM-SUITE project and the plan-only controls for cloud, WAS, runtime, and supply-chain governance. It is intentionally descriptive and non-executing: it documents controls, verification gates, and approval requirements without activating live cloud, Kubernetes, or deployment actions.

## Executive summary

The project integrates a layered defensive posture across:

- Cloud infrastructure security (AWS / Microsoft Azure)
- Web application and WAF review (WAS / defense in depth)
- Sigstore / Cosign signing and verification
- Falco runtime monitoring and workload rules
- CycloneDX / SPDX SBOM evaluation and CVE mapping
- Release gating with explicit verification gates

The model follows the repository convention of `PLAN_ONLY`, `NOT_EXECUTED`, and `NOT_IMPLEMENTED` for security actions that would otherwise operate on real infrastructure or production workloads.

## Critical review points

### 1. Cloud infrastructure controls

The cloud assessment module is a governance model, not an active cloud connector. It is designed to review:

- IAM and MFA posture
- encryption and key management
- network segmentation and private access patterns
- patching and image hygiene
- logging and threat detection
- WAF, firewall, and ingress controls

Operational expectation: the operator reviews recommended controls and maps them to concrete cloud accounts, policies, and lifecycle responsibilities before any production deployment.

### 2. Web application and defense-in-depth controls

The WAS / WAF layer documents a defense-in-depth model spanning:

- identity
- network
- application runtime
- data protection
- monitoring and response

This is a policy architecture intended for release review, not direct runtime enforcement.

### 3. Supply-chain controls

The supply-chain section emphasizes:

- OIDC-backed signing identity
- Fulcio/Sigstore certificate trust model
- Rekor provenance and transparency log verification
- in-toto attestation review
- SBOM generation and dependency review
- CVE correlation and compliance review

Release approval is gated on signed evidence, verified identity, reviewed attestation, and documented exception handling.

### 4. Runtime controls

Falco is represented as workload-specific detection logic for containers and Kubernetes.

Examples include:

- outbound connection anomalies for web/API workloads
- sensitive file writes or credential access attempts
- database-tier credential and privilege abuse detection
- LLM/inference workload model artifact access and suspicious execution patterns

These rules are presented as policy templates and require environment-specific tuning and approvals before production use.

## Control model

The project uses layered review gates before real promotion:

1. Sign artifact and verify identity
2. Validate provenance and digests
3. Check SBOM coverage and dependency quality
4. Map components to CVE feeds and policy exceptions
5. Review runtime monitoring policy and workload profile
6. Require compliance/security approval
7. Promote to production only after all gates pass

## Conclusion

This repository is best understood as a governance and policy planning toolkit for secure delivery. It supports security review and release readiness analysis without making live cloud or runtime changes. Production deployment still requires operator-owned controls, secret management, network isolation, and final approval in the target environment.
