# Phase 4 Live Ready Runbook: mission + collection + AI governance

## Scope
This phase covers:
- XKeyscore / Boundless Informant style collection integration
- Mission control / US-984XN style workflow integration
- Graph fusion / Palantir Foundry / Sec-PaLM governance / model registry integration

## Required env vars
- [ ] `SANCTUM_XKEYSCORE_API_URL`
- [ ] `SANCTUM_XKEYSCORE_TOKEN`
- [ ] `SANCTUM_BOUNDLESS_API_URL`
- [ ] `SANCTUM_BOUNDLESS_TOKEN`
- [ ] `SANCTUM_MISSION_API_URL`
- [ ] `SANCTUM_MISSION_API_TOKEN`
- [ ] `SANCTUM_SEC_PALM_MODEL_REGISTRY`
- [ ] `SANCTUM_MODEL_REGISTRY_URL`
- [ ] `SANCTUM_MODEL_GOVERNANCE_TOKEN`
- [ ] `SANCTUM_PALANTIR_FOUNDRY_API_URL`
- [ ] `SANCTUM_DATA_FUSION_URL`
- [ ] `SANCTUM_DATA_FUSION_TOKEN`

## Gate checklist
- [ ] Collection systems are reachable and auth-valid
- [ ] Mission API responds with a live status and scope context
- [ ] Model governance endpoint is available and protected
- [ ] Data fusion endpoint is authenticated and allowed to ingest structured evidence
- [ ] Data lineage and tenant boundaries are maintained
- [ ] Live evidence is stored and queryable without cross-tenant leakage
