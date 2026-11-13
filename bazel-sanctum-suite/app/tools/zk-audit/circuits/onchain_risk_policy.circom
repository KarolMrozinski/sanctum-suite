pragma circom 2.1.6;

include "circomlib/poseidon.circom";
include "circomlib/bitify.circom";
include "circomlib/comparators.circom";

template OnChainRiskPolicy(MAX_ASSESSMENTS) {
    signal input commitmentRoot;
    signal input assessmentCount;
    signal input policyId;
    signal input ratings[MAX_ASSESSMENTS];
    signal input salts[MAX_ASSESSMENTS];

    component countBits = Num2Bits(4);
    countBits.in <== assessmentCount;
    component countPositive = LessThan(4);
    countPositive.in[0] <== 0;
    countPositive.in[1] <== assessmentCount;
    countPositive.out === 1;
    component countWithinLimit = LessThan(4);
    countWithinLimit.in[0] <== assessmentCount;
    countWithinLimit.in[1] <== MAX_ASSESSMENTS + 1;
    countWithinLimit.out === 1;

    policyId === 1945772296728485777017022967566873140484147189102286400176588328429876240220;

    component leaves[MAX_ASSESSMENTS];
    component active[MAX_ASSESSMENTS];
    component ratingBits[MAX_ASSESSMENTS];
    component allowedRating[MAX_ASSESSMENTS];
    signal tree[2 * MAX_ASSESSMENTS - 1];
    component treeHashes[MAX_ASSESSMENTS - 1];

    for (var i = 0; i < MAX_ASSESSMENTS; i++) {
        active[i] = LessThan(4);
        active[i].in[0] <== i;
        active[i].in[1] <== assessmentCount;

        ratingBits[i] = Num2Bits(3);
        ratingBits[i].in <== ratings[i];

        allowedRating[i] = LessThan(3);
        allowedRating[i].in[0] <== ratings[i];
        allowedRating[i].in[1] <== 3;
        active[i].out * (1 - allowedRating[i].out) === 0;

        (1 - active[i].out) * ratings[i] === 0;
        (1 - active[i].out) * salts[i] === 0;

        leaves[i] = Poseidon(2);
        leaves[i].inputs[0] <== ratings[i];
        leaves[i].inputs[1] <== salts[i];
        tree[MAX_ASSESSMENTS - 1 + i] <== leaves[i].out;
    }

    for (var n = MAX_ASSESSMENTS - 1; n > 0; n--) {
        var parent = n - 1;
        treeHashes[parent] = Poseidon(2);
        treeHashes[parent].inputs[0] <== tree[2 * parent + 1];
        treeHashes[parent].inputs[1] <== tree[2 * parent + 2];
        tree[parent] <== treeHashes[parent].out;
    }

    commitmentRoot === tree[0];
}

component main {public [commitmentRoot, assessmentCount, policyId]} = OnChainRiskPolicy(8);
