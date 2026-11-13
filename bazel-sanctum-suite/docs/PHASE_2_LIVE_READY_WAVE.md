# Phase 2 live-ready backlog

This document captures the concrete implementation wave for the next operational expansion: legacy host baselines, embedded control-plane, graph/agentic AI, QKD, and neuromorphic compute. The model remains fail-closed: each capability becomes `READY` only when the operator supplies env vars, auth material, endpoint access, and runtime policy.

## Wave objective

Deliver a production-grade live-ready layer for the following capability IDs:

- `security-capability:os-baseline`
- `security-capability:embedded-control-plane`
- `security-capability:graph-ai`
- `security-capability:agentic-ai`
- `security-capability:key-distribution`
- `security-capability:neuromorphic-compute`
- `security-capability:long-term-storage`

## Module-by-module backlog

### 1) Legacy host baselines

- Capability ID: `security-capability:os-baseline`
- Modules: HP-UX, Oracle Solaris, OpenVMS
- Auth: bearer token or mTLS to the host inventory API
- Required env vars:
  - `SANCTUM_HOST_INVENTORY_URL`
  - `SANCTUM_HOST_API_TOKEN`
  - `SANCTUM_OS_FAMILY`
- Endpoint: `/api/v1/security-capabilities/security-capability:os-baseline/evidence`
- Payload shape:
  ```json
  {
    "target": "edge-domain",
    "environment": "production",
    "capability_id": "security-capability:os-baseline",
    "source_type": "asset_inventory",
    "evidence": {
      "os_family": "solaris",
      "patch_level": "2026.10",
      "host_inventory": ["host-01", "host-02"]
    },
    "status": "PLAN_ONLY"
  }
  ```

### 2) Embedded control plane (VxWorks)

- Capability ID: `security-capability:embedded-control-plane`
- Modules: VxWorks, embedded firmware control-plane
- Auth: mTLS + client certificate
- Required env vars:
  - `SANCTUM_VXWORKS_API_URL`
  - `SANCTUM_VXWORKS_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:embedded-control-plane/evidence`
- Payload shape:
  ```json
  {
    "target": "embedded-control-plane",
    "environment": "ot-domain",
    "capability_id": "security-capability:embedded-control-plane",
    "source_type": "firmware_api",
    "evidence": {
      "firmware_version": "7.3.4",
      "config_hash": "sha256:...",
      "network_policy": {"segment": "ot-1"}
    },
    "status": "PLAN_ONLY"
  }
  ```

### 3) Graph AI

- Capability ID: `security-capability:graph-ai`
- Modules: GNN, graph analytics, GNN model registry
- Auth: OAuth2 client credentials
- Required env vars:
  - `SANCTUM_GNN_MODEL_REGISTRY`
  - `SANCTUM_MODEL_API_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:graph-ai/evidence`
- Payload shape:
  ```json
  {
    "target": "intel-graph",
    "environment": "research",
    "capability_id": "security-capability:graph-ai",
    "source_type": "model_registry",
    "evidence": {
      "model_registry": "https://graph-model-registry.example",
      "model_version": "gnn-v3.12",
      "training_data": ["entity-graph"]
    },
    "status": "PLAN_ONLY"
  }
  ```

### 4) Agentic AI

- Capability ID: `security-capability:agentic-ai`
- Modules: autonomous agent runtime, tool permissions, execution guardrails
- Auth: bearer token scoped to agent runtime
- Required env vars:
  - `SANCTUM_AGENT_RUNTIME`
  - `SANCTUM_AGENT_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:agentic-ai/evidence`
- Payload shape:
  ```json
  {
    "target": "agent-orchestrator",
    "environment": "production",
    "capability_id": "security-capability:agentic-ai",
    "source_type": "agent_runtime",
    "evidence": {
      "runtime": "openai-agent-runtime",
      "tool_permissions": ["read_only", "network_scan"],
      "execution_logs": ["agent-001"]
    },
    "status": "PLAN_ONLY"
  }
  ```

### 5) QKD

- Capability ID: `security-capability:key-distribution`
- Modules: QKD KME, peer validation, link status
- Auth: mTLS or token-bound KME client
- Required env vars:
  - `SANCTUM_QKD_PEER_ID`
  - `SANCTUM_QKD_KME_URL`
  - `SANCTUM_QKD_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:key-distribution/evidence`
- Payload shape:
  ```json
  {
    "target": "quantum-link",
    "environment": "secure-core",
    "capability_id": "security-capability:key-distribution",
    "source_type": "key_manager",
    "evidence": {
      "peer_id": "peer-alpha",
      "link_status": "online",
      "key_id": "qkd-key-000913"
    },
    "status": "PLAN_ONLY"
  }
  ```

### 6) Neuromorphic compute

- Capability ID: `security-capability:neuromorphic-compute`
- Modules: Intel Loihi, IBM TrueNorth
- Auth: service-account or signed hardware attestation token
- Required env vars:
  - `SANCTUM_NEUROMORPHIC_ACCELERATOR`
  - `SANCTUM_NEUROMORPHIC_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:neuromorphic-compute/evidence`
- Payload shape:
  ```json
  {
    "target": "accelerator-cluster",
    "environment": "research",
    "capability_id": "security-capability:neuromorphic-compute",
    "source_type": "hardware_inventory",
    "evidence": {
      "accelerator": "loihi",
      "hardware_metadata": {"chip_id": "loihi-02"},
      "task_policy": {"isolation": "strict"}
    },
    "status": "PLAN_ONLY"
  }
  ```

### 7) Long-term archival storage

- Capability ID: `security-capability:long-term-storage`
- Modules: DNA data storage, archival retention policy
- Auth: signed storage admin token or service account
- Required env vars:
  - `SANCTUM_ARCHIVE_STORAGE_DRIVER`
  - `SANCTUM_ARCHIVE_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:long-term-storage/evidence`
- Payload shape:
  ```json
  {
    "target": "archive-store",
    "environment": "retention",
    "capability_id": "security-capability:long-term-storage",
    "source_type": "storage_registry",
    "evidence": {
      "driver": "dna-archive",
      "retention_policy": "active",
      "storage_status": "ready"
    },
    "status": "PLAN_ONLY"
  }
  ```

## Deployment order

1. Legacy host baselines and embedded control-plane
2. Graph AI and Agentic AI guardrails
3. QKD and neuromorphic attestation
4. Long-term preservation and archival validation

## Acceptance criteria

A capability is considered live-ready only if all of the following are true:

- required env vars are present
- auth material is valid and scoped
- endpoint connectivity is verified
- health check returns `READY` or `NOT_CONFIGURED`, never a false positive
- evidence is emitted using the common capability event schema

## Implementation note

The implementation in this codebase already includes the live-ready adapter model and the registry hooks for these wave-2 capabilities. The remaining work is operational enablement: configure the real environment, wire the auth, and move each module from `NOT_CONFIGURED` to `READY` only after endpoint validation.
