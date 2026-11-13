# Phase 5 Live Ready Runbook: retention + audit + compliance

## Scope
This phase covers:
- retention policy enforcement
- operational audit stream
- compliance and control cutover

## Required env vars
- [ ] `SANCTUM_RETENTION_POLICY_DB`
- [ ] `SANCTUM_AUDIT_LOG_STORE_URL`
- [ ] `SANCTUM_AUDIT_LOG_TOKEN`
- [ ] `SANCTUM_COMPLIANCE_FRAMEWORK`
- [ ] `SANCTUM_COMPLIANCE_API_URL`
- [ ] `SANCTUM_COMPLIANCE_TOKEN`

## Gate checklist
- [ ] Retention policy database is durable and writable
- [ ] Audit store accepts attested evidence and timestamps
- [ ] Compliance API is reachable and policy-approved
- [ ] Retention behavior is tested with dry-run or isolated test data
- [ ] Access logs and evidence retention match policy
- [ ] Final cutover is approved by compliance and platform owners
