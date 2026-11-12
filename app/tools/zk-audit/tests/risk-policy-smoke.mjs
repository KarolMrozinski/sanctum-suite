import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { buildPoseidon } from "circomlibjs";
import * as snarkjs from "snarkjs";
import { proveRiskPolicy } from "../scripts/prove-risk.mjs";
import { verifyRiskPolicy } from "../scripts/verify-risk.mjs";

const scratch = await mkdtemp(path.join(os.tmpdir(), "sanctum-zk-risk-smoke-"));
const files = (name) => path.join(scratch, name);
const POLICY_ID =
  "1945772296728485777017022967566873140484147189102286400176588328429876240220";
let curve;

try {
  const ptau0 = files("powersoftau-0.ptau");
  const ptau1 = files("powersoftau-1.ptau");
  const ptau2 = files("powersoftau-final.ptau");
  const zkey0 = files("risk-0.zkey");
  const zkey1 = files("risk-test-only.zkey");
  const verificationKeyFile = files("verification-key.json");

  curve = await snarkjs.curves.getCurveFromName("bn128");
  await snarkjs.powersOfTau.newAccumulator(curve, 13, ptau0);
  await snarkjs.powersOfTau.contribute(
    ptau0,
    ptau1,
    "PUBLIC TEST-ONLY CONTRIBUTION",
    "public deterministic test-only entropy; never use for production",
  );
  await snarkjs.powersOfTau.preparePhase2(ptau1, ptau2);
  await snarkjs.zKey.newZKey(
    "circuits/onchain_risk_policy.r1cs",
    ptau2,
    zkey0,
  );
  await snarkjs.zKey.contribute(
    zkey0,
    zkey1,
    "PUBLIC TEST-ONLY CONTRIBUTION",
    "public deterministic test-only entropy; never use for production",
  );
  const verificationKey = await snarkjs.zKey.exportVerificationKey(zkey1);
  await writeFile(verificationKeyFile, JSON.stringify(verificationKey));

  const proof = await proveRiskPolicy(
    ["unknown", "low", "medium", "low"],
    "circuits/onchain_risk_policy_js/onchain_risk_policy.wasm",
    zkey1,
    verificationKeyFile,
  );
  assert.equal(proof.assessment_count, 4);
  assert.equal(proof.public_signals[0], proof.commitment_root);
  assert.equal(
    await verifyRiskPolicy(proof, verificationKey),
    true,
  );

  await assert.rejects(
    proveRiskPolicy(
      ["low", "high"],
      "circuits/onchain_risk_policy_js/onchain_risk_policy.wasm",
      zkey1,
      verificationKeyFile,
    ),
    /exceeds medium/,
  );

  const poseidon = await buildPoseidon();
  const hash = (inputs) =>
    poseidon.F.toObject(poseidon(inputs.map(BigInt))).toString();
  const maliciousRatings = [3, 0, 0, 0, 0, 0, 0, 0];
  const maliciousSalts = ["1", "0", "0", "0", "0", "0", "0", "0"];
  let level = maliciousRatings.map((rating, index) =>
    hash([rating, maliciousSalts[index]]),
  );
  while (level.length > 1) {
    const next = [];
    for (let index = 0; index < level.length; index += 2) {
      next.push(hash([level[index], level[index + 1]]));
    }
    level = next;
  }
  await assert.rejects(
    snarkjs.groth16.fullProve(
      {
        commitmentRoot: level[0],
        assessmentCount: "1",
        policyId: POLICY_ID,
        ratings: maliciousRatings.map(String),
        salts: maliciousSalts,
      },
      "circuits/onchain_risk_policy_js/onchain_risk_policy.wasm",
      zkey1,
    ),
  );

  const tampered = structuredClone(proof);
  tampered.assessment_count = 3;
  await assert.rejects(
    verifyRiskPolicy(tampered, verificationKey),
    /invalid format or public inputs/,
  );
  console.log(
    "On-chain risk ZK policy smoke test passed (ephemeral test-only ceremony).",
  );
} finally {
  if (curve) await curve.terminate();
  await rm(scratch, { recursive: true, force: true });
}
