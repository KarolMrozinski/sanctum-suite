import * as snarkjs from "snarkjs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const BATCH_SIZE = Number(process.env.SANCTUM_ZK_BATCH_SIZE ?? "256");
const POLICY_HASH =
  "1841298221720545410680030688376092580199638229742508812536090285103057017068";

export async function verifyProofs(
  proofs,
  verificationKey,
  expectedRoot,
  expectedCount,
) {
  const count = Number(expectedCount);
  const expectedProofCount = Math.ceil(count / BATCH_SIZE);
  if (
    !Number.isSafeInteger(count) ||
    count < 1 ||
    count > 100000 ||
    !Array.isArray(proofs) ||
    proofs.length !== expectedProofCount
  ) {
    throw new Error("ZK proof bundle does not cover the complete audit snapshot.");
  }

  for (let index = 0; index < expectedProofCount; index += 1) {
    const entry = proofs[index];
    const eventCount = Math.min(BATCH_SIZE, count - index * BATCH_SIZE);
    const expectedSignals = [
      expectedRoot,
      String(index),
      String(eventCount),
      String(count),
      POLICY_HASH,
    ];
    if (
      !entry ||
      !Array.isArray(entry.public_signals) ||
      entry.public_signals.length !== expectedSignals.length ||
      entry.public_signals.some((signal, signalIndex) => signal !== expectedSignals[signalIndex])
    ) {
      throw new Error(`ZK proof chunk ${index} has invalid public inputs.`);
    }
    if (!(await snarkjs.groth16.verify(verificationKey, entry.public_signals, entry.proof))) {
      throw new Error(`ZK proof chunk ${index} failed verification.`);
    }
  }
  return true;
}

async function main() {
  const [proofFile, verificationKeyFile, expectedRoot, expectedCount] =
    process.argv.slice(2);
  if (!proofFile || !verificationKeyFile || !expectedRoot || !expectedCount) {
    throw new Error("Usage: verify.mjs <proof-file> <verification-key> <root> <record-count>");
  }

  let bundle;
  let verificationKey;
  try {
    bundle = JSON.parse(await readFile(proofFile, "utf8"));
  } catch {
    throw new Error("ZK proof bundle cannot be read as JSON.");
  }
  try {
    verificationKey = JSON.parse(await readFile(verificationKeyFile, "utf8"));
  } catch {
    throw new Error("Groth16 verification key cannot be read as JSON.");
  }
  await verifyProofs(
    bundle.proofs,
    verificationKey,
    expectedRoot,
    expectedCount,
  );
  process.stdout.write("Verified all Groth16 proof chunks.\n");
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(`ZK proof verification failed: ${error.message}`);
    process.exit(1);
  });
}
