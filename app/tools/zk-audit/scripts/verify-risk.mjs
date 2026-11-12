import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as snarkjs from "snarkjs";

const POLICY_ID =
  "1945772296728485777017022967566873140484147189102286400176588328429876240220";

export async function verifyRiskPolicy(bundle, verificationKey) {
  if (
    !bundle ||
    bundle.format !== "sanctum-onchain-risk-policy-proof-v1" ||
    bundle.policy !== "sanctum-provider-risk-at-most-medium-v1" ||
    bundle.policy_id !== POLICY_ID ||
    !Number.isInteger(bundle.assessment_count) ||
    bundle.assessment_count < 1 ||
    bundle.assessment_count > 8 ||
    typeof bundle.commitment_root !== "string" ||
    !/^\d+$/.test(bundle.commitment_root) ||
    !Array.isArray(bundle.public_signals) ||
    bundle.public_signals.length !== 3 ||
    bundle.public_signals[0] !== bundle.commitment_root ||
    bundle.public_signals[1] !== String(bundle.assessment_count) ||
    bundle.public_signals[2] !== POLICY_ID
  ) {
    throw new Error("Risk proof bundle has invalid format or public inputs.");
  }
  if (!(await snarkjs.groth16.verify(verificationKey, bundle.public_signals, bundle.proof))) {
    throw new Error("On-chain risk policy Groth16 proof failed verification.");
  }
  return true;
}

async function main() {
  const [proofFile, verificationKeyFile] = process.argv.slice(2);
  if (!proofFile || !verificationKeyFile) {
    throw new Error("Usage: verify-risk.mjs <proof-file> <verification-key>");
  }
  let bundle;
  let verificationKey;
  try {
    bundle = JSON.parse(await readFile(proofFile, "utf8"));
  } catch {
    throw new Error("Risk proof bundle cannot be read as JSON.");
  }
  try {
    verificationKey = JSON.parse(await readFile(verificationKeyFile, "utf8"));
  } catch {
    throw new Error("Groth16 verification key cannot be read as JSON.");
  }
  await verifyRiskPolicy(bundle, verificationKey);
  process.stdout.write(
    "Verified: committed provider-reported ratings satisfy the at-most-medium circuit rule.\n",
  );
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(`On-chain risk proof verification failed: ${error.message}`);
    process.exit(1);
  });
}
