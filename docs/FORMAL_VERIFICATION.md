# Formal verification scope

The initial TLA+ model covers the API authorization and audit boundary in
[AuthorizationAudit.tla](../formal/authorization-audit/AuthorizationAudit.tla).
TLC enumerates two tenants, the supported OIDC roles, read/write operations,
auditor-workflow scope, unscoped legacy routes, optional/required OPA
configuration, and OPA allow, deny, and unavailable outcomes.

The model checks that:

- A route cannot execute unless the local authorization check and configured
  OPA policy both allow it.
- Tenant-mismatched access cannot execute, even if OPA returns allow.
- Required-but-unconfigured OPA and OPA outages fail closed.
- Every executed operation has a prior recorded decision.
- The recorded decision and policy version remain consistent after route
  execution.
- A recorded decision and policy version match an immutable snapshot captured
  when the decision is first written.

Run the finite-state model locally with Java 17 or later and TLA+ tools 1.7.4:

```powershell
Invoke-WebRequest `
  -Uri "https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar" `
  -OutFile "$env:TEMP\tla2tools.jar"
java -cp "$env:TEMP\tla2tools.jar" tlc2.TLC `
  -config formal/authorization-audit/AuthorizationAudit.cfg `
  formal/authorization-audit/AuthorizationAudit.tla
```

CI downloads that pinned TLA+ tools release, verifies its SHA-256 digest, and
runs TLC on every push and pull request. A passing model establishes only the
listed invariants over this finite abstraction and these assumptions. It does
not prove that the Python code, deployed Rego policy, OPA service, database,
tenant mapping, cryptographic components, or infrastructure conform to the
model. Unit tests separately check the corresponding API behavior; operators
must deploy and review the versioned OPA policy.
