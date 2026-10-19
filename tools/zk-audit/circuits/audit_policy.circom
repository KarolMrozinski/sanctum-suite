pragma circom 2.1.6;

include "poseidon.circom";
include "bitify.circom";
include "comparators.circom";

template AuditPolicyBatch(BATCH_SIZE, PATH_DEPTH) {
    signal input globalRoot;
    signal input chunkIndex;
    signal input eventCount;
    signal input totalRecordCount;
    signal input policyHash;
    signal input eventType[BATCH_SIZE];
    signal input decision[BATCH_SIZE];
    signal input outcome[BATCH_SIZE];
    signal input engine[BATCH_SIZE];
    signal input hasPolicyVersion[BATCH_SIZE];
    signal input salt[BATCH_SIZE];
    signal input siblingPath[PATH_DEPTH];

    component indexBits = Num2Bits(PATH_DEPTH);
    indexBits.in <== chunkIndex;

    component totalLimit = LessThan(17);
    totalLimit.in[0] <== totalRecordCount;
    totalLimit.in[1] <== 100001;
    totalLimit.out === 1;

    component chunkHasRecords = LessThan(17);
    chunkHasRecords.in[0] <== chunkIndex * BATCH_SIZE;
    chunkHasRecords.in[1] <== totalRecordCount;
    chunkHasRecords.out === 1;

    signal recordsRemaining;
    recordsRemaining <== totalRecordCount - chunkIndex * BATCH_SIZE;

    component moreThanBatch = LessThan(17);
    moreThanBatch.in[0] <== BATCH_SIZE;
    moreThanBatch.in[1] <== recordsRemaining;

    component positiveEventCount = LessThan(9);
    positiveEventCount.in[0] <== 0;
    positiveEventCount.in[1] <== eventCount;
    positiveEventCount.out === 1;

    component eventCountLimit = LessThan(9);
    eventCountLimit.in[0] <== eventCount;
    eventCountLimit.in[1] <== BATCH_SIZE + 1;
    eventCountLimit.out === 1;

    moreThanBatch.out * (eventCount - BATCH_SIZE) === 0;
    (1 - moreThanBatch.out) * (eventCount - recordsRemaining) === 0;

    policyHash === 1841298221720545410680030688376092580199638229742508812536090285103057017068;

    component isActive[BATCH_SIZE];
    component isStart[BATCH_SIZE];
    component isCompleted[BATCH_SIZE];
    component isStoragePreflight[BATCH_SIZE];
    component isDecisionAllow[BATCH_SIZE];
    component isDecisionDeny[BATCH_SIZE];
    component isEngineOpa[BATCH_SIZE];
    component decisionLimit[BATCH_SIZE];
    component outcomeAtLeast100[BATCH_SIZE];
    component outcomeBelow600[BATCH_SIZE];
    component outcomeBelow200[BATCH_SIZE];
    component outcomeBelow300[BATCH_SIZE];
    component engineLimit[BATCH_SIZE];
    component policyVersionIsBit[BATCH_SIZE];
    component isOpaEngine[BATCH_SIZE][5];
    signal isTwoHundred[BATCH_SIZE];
    signal isTwoHundredSeries[BATCH_SIZE];
    signal isOpaWithoutVersion[BATCH_SIZE];
    signal isDeniedCompleted[BATCH_SIZE];

    component leaves[BATCH_SIZE];
    signal tree[2 * BATCH_SIZE - 1];
    component treeHashes[BATCH_SIZE - 1];

    for (var i = 0; i < BATCH_SIZE; i++) {
        isActive[i] = LessThan(9);
        isActive[i].in[0] <== i;
        isActive[i].in[1] <== eventCount;

        isStart[i] = IsEqual();
        isStart[i].in[0] <== eventType[i];
        isStart[i].in[1] <== 0;
        isCompleted[i] = IsEqual();
        isCompleted[i].in[0] <== eventType[i];
        isCompleted[i].in[1] <== 1;
        isStoragePreflight[i] = IsEqual();
        isStoragePreflight[i].in[0] <== eventType[i];
        isStoragePreflight[i].in[1] <== 2;

        isActive[i].out * (1 - isStart[i].out - isCompleted[i].out - isStoragePreflight[i].out) === 0;
        (1 - isActive[i].out) * (eventType[i] - 3) === 0;
        (1 - isActive[i].out) * decision[i] === 0;
        (1 - isActive[i].out) * outcome[i] === 0;
        (1 - isActive[i].out) * engine[i] === 0;
        (1 - isActive[i].out) * hasPolicyVersion[i] === 0;
        (1 - isActive[i].out) * salt[i] === 0;

        policyVersionIsBit[i] = IsEqual();
        policyVersionIsBit[i].in[0] <== hasPolicyVersion[i] * (hasPolicyVersion[i] - 1);
        policyVersionIsBit[i].in[1] <== 0;

        isDecisionAllow[i] = IsEqual();
        isDecisionAllow[i].in[0] <== decision[i];
        isDecisionAllow[i].in[1] <== 0;
        isDecisionDeny[i] = IsEqual();
        isDecisionDeny[i].in[0] <== decision[i];
        isDecisionDeny[i].in[1] <== 1;
        decisionLimit[i] = LessThan(9);
        decisionLimit[i].in[0] <== decision[i];
        decisionLimit[i].in[1] <== 3;
        engineLimit[i] = LessThan(9);
        engineLimit[i].in[0] <== engine[i];
        engineLimit[i].in[1] <== 11;
        outcomeAtLeast100[i] = LessThan(10);
        outcomeAtLeast100[i].in[0] <== 99;
        outcomeAtLeast100[i].in[1] <== outcome[i];
        outcomeBelow600[i] = LessThan(10);
        outcomeBelow600[i].in[0] <== outcome[i];
        outcomeBelow600[i].in[1] <== 600;
        outcomeBelow200[i] = LessThan(10);
        outcomeBelow200[i].in[0] <== outcome[i];
        outcomeBelow200[i].in[1] <== 200;
        outcomeBelow300[i] = LessThan(10);
        outcomeBelow300[i].in[0] <== outcome[i];
        outcomeBelow300[i].in[1] <== 300;

        for (var j = 0; j < 5; j++) {
            var opaEngineCodes[5] = [1, 2, 6, 8, 10];
            isOpaEngine[i][j] = IsEqual();
            isOpaEngine[i][j].in[0] <== engine[i];
            isOpaEngine[i][j].in[1] <== opaEngineCodes[j];
        }
        isEngineOpa[i] = IsEqual();
        isEngineOpa[i].in[0] <== isOpaEngine[i][0].out + isOpaEngine[i][1].out + isOpaEngine[i][2].out + isOpaEngine[i][3].out + isOpaEngine[i][4].out;
        isEngineOpa[i].in[1] <== 1;

        isCompleted[i].out * (1 - policyVersionIsBit[i].out) === 0;
        decisionLimit[i].out * isCompleted[i].out === isCompleted[i].out;
        engineLimit[i].out * isCompleted[i].out === isCompleted[i].out;
        outcomeAtLeast100[i].out * isCompleted[i].out === isCompleted[i].out;
        outcomeBelow600[i].out * isCompleted[i].out === isCompleted[i].out;
        isOpaWithoutVersion[i] <== isEngineOpa[i].out * (1 - hasPolicyVersion[i]);
        isOpaWithoutVersion[i] * isCompleted[i].out === 0;

        isTwoHundred[i] <== (1 - outcomeBelow200[i].out) * outcomeBelow300[i].out;
        isTwoHundredSeries[i] <== isTwoHundred[i] * isCompleted[i].out;
        isTwoHundredSeries[i] * (1 - isDecisionAllow[i].out) === 0;
        isDeniedCompleted[i] <== isDecisionDeny[i].out * isCompleted[i].out;
        isDeniedCompleted[i] * (outcome[i] - 403) === 0;

        leaves[i] = Poseidon(6);
        leaves[i].inputs[0] <== eventType[i];
        leaves[i].inputs[1] <== decision[i];
        leaves[i].inputs[2] <== outcome[i];
        leaves[i].inputs[3] <== engine[i];
        leaves[i].inputs[4] <== hasPolicyVersion[i];
        leaves[i].inputs[5] <== salt[i];
        tree[BATCH_SIZE - 1 + i] <== leaves[i].out;
    }

    for (var n = BATCH_SIZE - 1; n > 0; n--) {
        var parent = n - 1;
        treeHashes[parent] = Poseidon(2);
        treeHashes[parent].inputs[0] <== tree[2 * parent + 1];
        treeHashes[parent].inputs[1] <== tree[2 * parent + 2];
        tree[parent] <== treeHashes[parent].out;
    }

    signal pathLeft[PATH_DEPTH];
    signal pathRight[PATH_DEPTH];
    signal pathNodes[PATH_DEPTH + 1];
    component pathHashes[PATH_DEPTH];
    pathNodes[0] <== tree[0];
    for (var level = 0; level < PATH_DEPTH; level++) {
        pathLeft[level] <== pathNodes[level] + indexBits.out[level] * (siblingPath[level] - pathNodes[level]);
        pathRight[level] <== siblingPath[level] + indexBits.out[level] * (pathNodes[level] - siblingPath[level]);
        pathHashes[level] = Poseidon(2);
        pathHashes[level].inputs[0] <== pathLeft[level];
        pathHashes[level].inputs[1] <== pathRight[level];
        pathNodes[level + 1] <== pathHashes[level].out;
    }
    globalRoot === pathNodes[PATH_DEPTH];
}
