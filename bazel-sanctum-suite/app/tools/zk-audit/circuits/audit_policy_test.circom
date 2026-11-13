pragma circom 2.1.6;

include "audit_policy.circom";

component main {public [globalRoot, chunkIndex, eventCount, totalRecordCount, policyHash]} = AuditPolicyBatch(2, 1);
