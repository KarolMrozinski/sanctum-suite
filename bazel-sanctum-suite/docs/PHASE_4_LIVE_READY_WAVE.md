# Phase 4 live-ready wave

This wave continues the live-ready rollout for long-tail operational and governance modules: mission integration, signals intelligence, collection intelligence, long-term storage, and compliance/governance surfaces.

## Objective

Deploy the next live-ready capability layer for:

- `security-capability:signals-intel`
- `security-capability:collection-intel`
- `security-capability:mission-integration`
- `security-capability:long-term-storage`
- `security-capability:ai-governance`
- `security-capability:graph-data-fusion`

## Module-by-module backlog

### 1) Signals intelligence

- Modules: XKeyscore
- Capability ID: `security-capability:signals-intel`
- Auth: API key or signed request token
- Required env vars:
  - `SANCTUM_XKEYSCORE_API_URL`
  - `SANCTUM_XKEYSCORE_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:signals-intel/evidence`
- Payload:
  ```json
  {
    "capability_id": "security-capability:signals-intel",
    "source_type": "signals_api",
    "evidence": {
      "query_scope": "targeted-intel",
      "collection_status": "online",
      "metadata": {"source": "xkeyscore"}
    },
    "status": "PLAN_ONLY"
  }
  ```

### 2) Collection intelligence

- Modules: Boundless Informant
- Capability ID: `security-capability:collection-intel`
- Auth: bearer token
- Required env vars:
  - `SANCTUM_BOUNDLESS_API_URL`
  - `SANCTUM_BOUNDLESS_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:collection-intel/evidence`
- Payload:
  ```json
  {
    "capability_id": "security-capability:collection-intel",
    "source_type": "collection_api",
    "evidence": {
      "collection_id": "collection-12",
      "collection_status": "active",
      "reporting_window": "last-7d"
    },
    "status": "PLAN_ONLY"
  }
  ```

### 3) Mission integration

- Modules: US-984XN / PRISM mission integration
- Capability ID: `security-capability:mission-integration`
- Auth: JWT bearer token, policy-bound
- Required env vars:
  - `SANCTUM_MISSION_API_URL`
  - `SANCTUM_MISSION_API_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:mission-integration/evidence`
- Payload:
  ```json
  {
    "capability_id": "security-capability:mission-integration",
    "source_type": "mission_api",
    "evidence": {
      "mission_id": "mission-arc",
      "correlation_id": "corr-1189",
      "telemetry": {"status": "active"}
    },
    "status": "PLAN_ONLY"
  }
  ```

### 4) Long-term storage

- Modules: DNA Data Storage, archival retention
- Capability ID: `security-capability:long-term-storage`
- Auth: service account or signed archive token
- Required env vars:
  - `SANCTUM_ARCHIVE_STORAGE_DRIVER`
  - `SANCTUM_ARCHIVE_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:long-term-storage/evidence`
- Payload:
  ```json
  {
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

### 5) AI governance and graph fusion

- Modules: Sec-PaLM, Palantir Gotham / Foundry
- Capability IDs:
  - `security-capability:ai-governance`
  - `security-capability:graph-data-fusion`
- Auth: OAuth2 + policy-bound service account
- Required env vars:
  - `SANCTUM_MODEL_REGISTRY_URL`
  - `SANCTUM_MODEL_GOVERNANCE_TOKEN`
  - `SANCTUM_DATA_FUSION_URL`
- Endpoint examples:
  - `/api/v1/security-capabilities/security-capability:ai-governance/evidence`
  - `/api/v1/security-capabilities/security-capability:graph-data-fusion/evidence`

## Deployment order

1. Signals and collection intelligence
2. Mission integration
3. Long-term storage and archival validation
4. AI governance and graph fusion
5. Health verification and operational cutover

## Acceptance criteria

A module is accepted as live-ready only when:

- env vars are present and valid
- auth is scoped to minimum required permissions
- endpoint health check succeeds or returns a clear `NOT_CONFIGURED`
- event payload is emitted in the common capability schema
- the adapter is present in the registry and can be called by capability ID
