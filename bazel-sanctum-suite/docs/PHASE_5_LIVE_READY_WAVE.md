# Phase 5 live-ready wave

This final intelligence and governance wave completes the live-ready rollout for mission, signals, data fusion, archive retention, and AI governance.

## Objective

Move the following capability IDs into a controlled live-ready deployment model:

- `security-capability:signals-intel`
- `security-capability:collection-intel`
- `security-capability:mission-integration`
- `security-capability:long-term-storage`
- `security-capability:ai-governance`
- `security-capability:graph-data-fusion`

## Module-by-module backlog

### 1) Signals intelligence (XKeyscore)

- Capability ID: `security-capability:signals-intel`
- Auth: API key or signed request token
- Required env vars:
  - `SANCTUM_XKEYSCORE_API_URL`
  - `SANCTUM_XKEYSCORE_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:signals-intel/evidence`
- Sample payload:
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

### 2) Collection intelligence (Boundless Informant)

- Capability ID: `security-capability:collection-intel`
- Auth: bearer token
- Required env vars:
  - `SANCTUM_BOUNDLESS_API_URL`
  - `SANCTUM_BOUNDLESS_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:collection-intel/evidence`
- Sample payload:
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

### 3) Mission integration (US-984XN / PRISM)

- Capability ID: `security-capability:mission-integration`
- Auth: JWT bearer token, policy-bound
- Required env vars:
  - `SANCTUM_MISSION_API_URL`
  - `SANCTUM_MISSION_API_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:mission-integration/evidence`
- Sample payload:
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

### 4) Long-term retention and archive

- Capability ID: `security-capability:long-term-storage`
- Auth: service account or signed archive token
- Required env vars:
  - `SANCTUM_ARCHIVE_STORAGE_DRIVER`
  - `SANCTUM_ARCHIVE_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:long-term-storage/evidence`
- Sample payload:
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

### 5) AI governance (Sec-PaLM)

- Capability ID: `security-capability:ai-governance`
- Auth: OAuth2 client credentials
- Required env vars:
  - `SANCTUM_MODEL_REGISTRY_URL`
  - `SANCTUM_MODEL_GOVERNANCE_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:ai-governance/evidence`
- Sample payload:
  ```json
  {
    "capability_id": "security-capability:ai-governance",
    "source_type": "model_registry",
    "evidence": {
      "model_registry": "https://model-registry.internal",
      "risk_policy": "tier-1",
      "guardrail_config": {"policy": "strict"}
    },
    "status": "PLAN_ONLY"
  }
  ```

### 6) Graph data fusion (Palantir Gotham / Foundry)

- Capability ID: `security-capability:graph-data-fusion`
- Auth: OAuth2 client credentials or signed token
- Required env vars:
  - `SANCTUM_DATA_FUSION_URL`
  - `SANCTUM_DATA_FUSION_TOKEN`
- Endpoint: `/api/v1/security-capabilities/security-capability:graph-data-fusion/evidence`
- Sample payload:
  ```json
  {
    "capability_id": "security-capability:graph-data-fusion",
    "source_type": "data_platform_api",
    "evidence": {
      "source_data": ["intel-feed"],
      "data_contracts": ["restricted"],
      "classification_tags": ["TS"]
    },
    "status": "PLAN_ONLY"
  }
  ```

## Deployment order

1. Signals and collection intelligence
2. Mission integration
3. Long-term archival storage
4. AI governance and graph fusion
5. Final operational validation and event publication

## Acceptance criteria

A module is considered live-ready only when:

- env vars are defined and validated for the target infrastructure
- auth is scoped to the minimal required permission set
- health check does not falsely claim readiness
- evidence is emitted through the common capability event schema
- the adapter is registered in the central capability registry and callable by capability ID
