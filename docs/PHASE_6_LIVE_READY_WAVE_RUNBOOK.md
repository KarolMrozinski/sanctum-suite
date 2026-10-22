# Phase 6 Live Ready Runbook: final production cutover

## Scope
This final phase marks the supervised production transition after the earlier waves have passed their operational gates.

## Final gate checklist
- [ ] Phase 1, 2, 3, 4, and 5 gates are all complete
- [ ] Real credentials and endpoint config are present in the target environment
- [ ] RBAC, network policy, and tenant isolation are validated
- [ ] CI/CD and GitOps sync are green
- [ ] Production audit logs are active
- [ ] Retention policy and compliance checks are active
- [ ] Manual approval is recorded by platform and security owners
- [ ] No capability remains in `NOT_CONFIGURED` for production service paths

## Production signoff template
```yaml
production_signoff:
  platform_owner: ""
  security_owner: ""
  compliance_owner: ""
  date_utc: "2026-10-22T00:00:00Z"
  approved_wave: "phase-6"
  status: "READY"
```
