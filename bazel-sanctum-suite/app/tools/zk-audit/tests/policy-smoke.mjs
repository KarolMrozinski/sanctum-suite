import assert from "node:assert/strict";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import * as snarkjs from "snarkjs";

process.env.SANCTUM_ZK_BATCH_SIZE = "2";
process.env.SANCTUM_ZK_TREE_DEPTH = "1";
const { createProofs } = await import("../scripts/prove.mjs");
const { verifyProofs } = await import("../scripts/verify.mjs");
const scratch = await mkdtemp(path.join(os.tmpdir(), "sanctum-zk-smoke-"));
const files = (name) => path.join(scratch, name);
let curve;

try {
  const ptau0 = files("powersoftau-0.ptau");
  const ptau1 = files("powersoftau-1.ptau");
  const ptau2 = files("powersoftau-final.ptau");
  const zkey0 = files("audit-0.zkey");
  const zkey1 = files("audit-test-only.zkey");
  const verificationKey = files("verification-key.json");

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
    "circuits/audit_policy_test.r1cs",
    ptau2,
    zkey0,
  );
  await snarkjs.zKey.contribute(
    zkey0,
    zkey1,
    "PUBLIC TEST-ONLY CONTRIBUTION",
    "public deterministic test-only entropy; never use for production",
  );
  const verificationDocument = await snarkjs.zKey.exportVerificationKey(zkey1);
  await writeFile(verificationKey, JSON.stringify(verificationDocument));

  const events = [
    {
      event_type: 1,
      decision: 0,
      outcome: 200,
      engine: 1,
      has_policy_version: 1,
    },
    {
      event_type: 1,
      decision: 1,
      outcome: 403,
      engine: 0,
      has_policy_version: 0,
    },
    {
      event_type: 0,
      decision: 2,
      outcome: 0,
      engine: 0,
      has_policy_version: 0,
    },
  ];
  const generated = await createProofs(
    events,
    "circuits/audit_policy_test_js/audit_policy_test.wasm",
    zkey1,
    verificationKey,
  );
  assert.equal(
    await verifyProofs(
      generated.proofs,
      verificationDocument,
      generated.global_root,
      events.length,
    ),
    true,
  );

  const invalidEvents = structuredClone(events);
  invalidEvents[0].decision = 1;
  await assert.rejects(
    createProofs(
      invalidEvents,
      "circuits/audit_policy_test_js/audit_policy_test.wasm",
      zkey1,
      verificationKey,
    ),
  );

  const invalidOpaEvents = structuredClone(events);
  invalidOpaEvents[0].has_policy_version = 0;
  await assert.rejects(
    createProofs(
      invalidOpaEvents,
      "circuits/audit_policy_test_js/audit_policy_test.wasm",
      zkey1,
      verificationKey,
    ),
  );

  await assert.rejects(
    verifyProofs(
      generated.proofs.slice(1),
      verificationDocument,
      generated.global_root,
      events.length,
    ),
    /complete audit snapshot/,
  );

  const tampered = structuredClone(generated.proofs);
  tampered[0].public_signals[0] = "1";
  await assert.rejects(
    verifyProofs(
      tampered,
      verificationDocument,
      generated.global_root,
      events.length,
    ),
    /invalid public inputs|failed verification/,
  );
  console.log("Groth16 audit policy smoke test passed (ephemeral test-only ceremony).");
} finally {
  if (curve) await curve.terminate();
  await rm(scratch, { recursive: true, force: true });
}
