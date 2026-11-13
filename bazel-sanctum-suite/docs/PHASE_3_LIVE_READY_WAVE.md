# Phase 3 live-ready wave

This document captures the next complete implementation wave: legacy host baselines, embedded control-plane, graph and agentic AI, QKD key distribution, and neuromorphic compute.

## Objective

Move the following capability IDs into a real deployment pattern with environment-specific env vars, scoped authentication, live health checks, and event publication:

- `security-capability:os-baseline`
- `security-capability:embedded-control-plane`
- `security-capability:graph-ai`
- `security-capability:agentic-ai`
- `security-capability:key-distribution`
- `security-capability:neuromorphic-compute`

## Module-by-module backlog

### 1) Legacy host baselines

- Modules: HP-UX, Oracle Solaris, OpenVMS
- Capability ID: `security-capability:os-baseline`
- Auth: bearer token or mutual TLS, dependent on inventory service
- Required env vars:
  - `SANCTUM_HOST_INVENTORY_URL`
  - `SANCTUM_HOST_API_TOKEN`
  - `SANCTUM_OS_FAMILY`
- Endpoint: `/api/v1/security-capabilities/security-capability:os-baseline/evidence`
- Payload:
  ```json
  {
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

### 2) Embedded control-plane (VxWorks)

- Modules: VxWorks
- Capability ID: `security-capability:embedded-control-plane`
- Auth: mTLS with client cert
- Required env vars:
  - `SANCTUM_VXWORKS_API_URL`
  - `SANCTUM_VXWORKS_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:embedded-control-plane/evidence`
- Payload:
  ```json
  {
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

### 3) Graph AI / GNN

- Modules: GNN, graph analytics, model registry
- Capability ID: `security-capability:graph-ai`
- Auth: OAuth2 client credentials
- Required env vars:
  - `SANCTUM_GNN_MODEL_REGISTRY`
  - `SANCTUM_MODEL_API_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:graph-ai/evidence`
- Payload:
  ```json
  {
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

- Modules: Autonomous Agents AI (Agentic AI)
- Capability ID: `security-capability:agentic-ai`
- Auth: bearer token scoped to runtime
- Required env vars:
  - `SANCTUM_AGENT_RUNTIME`
  - `SANCTUM_AGENT_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:agentic-ai/evidence`
- Payload:
  ```json
  {
    "capability_id": "security-capability:agentic-ai",
    "source_type": "agent_runtime",
    "evidence": {
      "runtime": "agent-runtime",
      "tool_permissions": ["read_only", "network_scan"],
      "execution_logs": ["agent-001"]
    },
    "status": "PLAN_ONLY"
  }
  ```

### 5) QKD key distribution

- Modules: QKD
- Capability ID: `security-capability:key-distribution`
- Auth: mTLS or KME signed token
- Required env vars:
  - `SANCTUM_QKD_PEER_ID`
  - `SANCTUM_QKD_KME_URL`
  - `SANCTUM_QKD_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:key-distribution/evidence`
- Payload:
  ```json
  {
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

- Modules: Intel Loihi, IBM TrueNorth
- Capability ID: `security-capability:neuromorphic-compute`
- Auth: service account or signed accelerator attestation
- Required env vars:
  - `SANCTUM_NEUROMORPHIC_ACCELERATOR`
  - `SANCTUM_NEUROMORPHIC_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:neuromorphic-compute/evidence`
- Payload:
  ```json
  {
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

## Deployment order

1. Legacy host baselines and embedded control-plane
2. Graph and Agentic AI
3. QKD and neuromorphic attestation
4. Health-check validation, event publication, and production gating

## Acceptance criteria

A module is accepted as live-ready only when all of the following are true:

- env vars are present and correctly scoped
- auth method matches the external API contract
- endpoint checks pass in the target environment
- health-check returns `READY` or `NOT_CONFIGURED`, never a false positive
- events are produced in the common `sanctum-capability-event-v1` schema
