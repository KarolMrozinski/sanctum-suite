------------------------------ MODULE AuthorizationAudit ------------------------------
EXTENDS TLC

CONSTANTS
    Tenants,
    Roles,
    Methods,
    OPAModes,
    OPAResults,
    Decisions,
    AuditDecisions,
    PolicyVersions

VARIABLES
    userTenant,
    resourceTenant,
    userRole,
    requestMethod,
    auditorWorkflow,
    unscopedRoute,
    opaMode,
    opaResult,
    decision,
    decisionVersion,
    auditRecorded,
    auditDecision,
    auditVersion,
    auditSnapshotDecision,
    auditSnapshotVersion,
    routeExecuted

vars ==
    << userTenant, resourceTenant, userRole, requestMethod, auditorWorkflow,
       unscopedRoute, opaMode, opaResult, decision, decisionVersion, auditRecorded,
       auditDecision, auditVersion, auditSnapshotDecision,
       auditSnapshotVersion, routeExecuted >>

LocalAllowed ==
    userTenant = resourceTenant
    /\ ~unscopedRoute
    /\ (userRole = "ADMIN"
        \/ requestMethod = "READ"
        \/ (userRole = "AUDITOR" /\ requestMethod = "WRITE" /\ auditorWorkflow))

PolicyDecision ==
    IF opaResult = "UNAVAILABLE"
        \/ (opaMode = "REQUIRED" /\ opaResult = "NOT_CONFIGURED")
    THEN "ERROR"
    ELSE IF ~LocalAllowed
    THEN "DENY"
    ELSE IF opaResult = "NOT_CONFIGURED" /\ opaMode = "OPTIONAL"
    THEN "ALLOW"
    ELSE IF opaResult = "ALLOW"
    THEN "ALLOW"
    ELSE "DENY"

PolicyVersion ==
    IF opaResult \in {"ALLOW", "DENY"}
    THEN "POLICY_V1"
    ELSE "NO_VERSION"

Init ==
    /\ userTenant \in Tenants
    /\ resourceTenant \in Tenants
    /\ userRole \in Roles
    /\ requestMethod \in Methods
    /\ auditorWorkflow \in BOOLEAN
    /\ unscopedRoute \in BOOLEAN
    /\ opaMode \in OPAModes
    /\ opaResult \in OPAResults
    /\ decision = "PENDING"
    /\ decisionVersion = "NO_VERSION"
    /\ auditRecorded = FALSE
    /\ auditDecision = "NO_DECISION"
    /\ auditVersion = "NO_VERSION"
    /\ auditSnapshotDecision = "NO_DECISION"
    /\ auditSnapshotVersion = "NO_VERSION"
    /\ routeExecuted = FALSE

Evaluate ==
    /\ decision = "PENDING"
    /\ decision' = PolicyDecision
    /\ decisionVersion' = PolicyVersion
    /\ auditRecorded' = TRUE
    /\ auditDecision' = PolicyDecision
    /\ auditVersion' = PolicyVersion
    /\ auditSnapshotDecision' = PolicyDecision
    /\ auditSnapshotVersion' = PolicyVersion
    /\ UNCHANGED << userTenant, resourceTenant, userRole, requestMethod,
                    auditorWorkflow, unscopedRoute, opaMode, opaResult, routeExecuted >>

Execute ==
    /\ decision = "ALLOW"
    /\ auditRecorded
    /\ ~routeExecuted
    /\ routeExecuted' = TRUE
    /\ UNCHANGED << userTenant, resourceTenant, userRole, requestMethod,
                    auditorWorkflow, unscopedRoute, opaMode, opaResult, decision,
                    decisionVersion, auditRecorded, auditDecision, auditVersion,
                    auditSnapshotDecision, auditSnapshotVersion >>

Next == Evaluate \/ Execute

Spec == Init /\ [][Next]_vars

TypeOK ==
    /\ userTenant \in Tenants
    /\ resourceTenant \in Tenants
    /\ userRole \in Roles
    /\ requestMethod \in Methods
    /\ auditorWorkflow \in BOOLEAN
    /\ unscopedRoute \in BOOLEAN
    /\ opaMode \in OPAModes
    /\ opaResult \in OPAResults
    /\ decision \in Decisions
    /\ decisionVersion \in PolicyVersions
    /\ auditRecorded \in BOOLEAN
    /\ auditDecision \in AuditDecisions
    /\ auditVersion \in PolicyVersions
    /\ auditSnapshotDecision \in AuditDecisions
    /\ auditSnapshotVersion \in PolicyVersions
    /\ routeExecuted \in BOOLEAN

NoUnauthorizedExecution ==
    routeExecuted =>
        decision = "ALLOW"
        /\ LocalAllowed
        /\ (opaResult = "ALLOW"
            \/ (opaMode = "OPTIONAL" /\ opaResult = "NOT_CONFIGURED"))

NoCrossTenantExecution ==
    routeExecuted => userTenant = resourceTenant

NoExecutionWithoutAudit ==
    routeExecuted => auditRecorded /\ auditDecision = "ALLOW"

FailuresFailClosed ==
    (opaResult = "UNAVAILABLE"
        \/ (opaMode = "REQUIRED" /\ opaResult = "NOT_CONFIGURED"))
    => decision # "ALLOW" /\ ~routeExecuted

DeniedRequestsDoNotExecute ==
    decision \in {"DENY", "ERROR"} => ~routeExecuted

AuditMatchesDecision ==
    auditRecorded =>
        auditDecision = decision /\ auditVersion = decisionVersion

AuditIsImmutable ==
    auditRecorded =>
        auditDecision = auditSnapshotDecision
        /\ auditVersion = auditSnapshotVersion

=============================================================================
