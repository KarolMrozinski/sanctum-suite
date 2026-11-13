import { randomBytes } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildPoseidon } from "circomlibjs";
import * as snarkjs from "snarkjs";

const MAX_ASSESSMENTS = 8;
const POLICY_ID =
  "1945772296728485777017022967566873140484147189102286400176588328429876240220";
const FIELD_MODULUS =
  21888242871839275222246405745257275088548364400416034343698204186575808495617n;
const RATING_CODES = {
  unknown: 0,
  low: 1,
  medium: 2,
  high: 3,
  severe: 4,
};

function hash(poseidon, inputs) {
  return poseidon.F.toObject(poseidon(inputs.map(BigInt))).toString();
}

export async function proveRiskPolicy(ratings, wasmPath, provingKeyPath, verificationKeyPath) {
  if (
    !Array.isArray(ratings) ||
    ratings.length < 1 ||
    ratings.length > MAX_ASSESSMENTS ||
    ratings.some((rating) => !Object.hasOwn(RATING_CODES, rating))
  ) {
    throw new Error("Risk proof input must contain 1-8 supported provider rating bands.");
  }
  const codes = ratings.map((rating) => RATING_CODES[rating]);
  if (codes.some((rating) => rating > 2)) {
    throw new Error("Risk policy is not satisfied: a provider-reported rating exceeds medium.");
  }

  const poseidon = await buildPoseidon();
  const paddedRatings = [...codes];
  const salts = codes.map(
    () => (BigInt(`0x${randomBytes(31).toString("hex")}`) % FIELD_MODULUS).toString(),
  );
  while (paddedRatings.length < MAX_ASSESSMENTS) paddedRatings.push(0);
  while (salts.length < MAX_ASSESSMENTS) salts.push("0");

  const leaves = paddedRatings.map((rating, index) =>
    hash(poseidon, [rating, salts[index]]),
  );
  let level = leaves;
  while (level.length > 1) {
    const next = [];
    for (let index = 0; index < level.length; index += 2) {
      next.push(hash(poseidon, [level[index], level[index + 1]]));
    }
    level = next;
  }
  const commitmentRoot = level[0];
  const witness = {
    commitmentRoot,
    assessmentCount: String(ratings.length),
    policyId: POLICY_ID,
    ratings: paddedRatings.map(String),
    salts,
  };
  const proofResult = await snarkjs.groth16.fullProve(witness, wasmPath, provingKeyPath);
  const verificationKey = JSON.parse(await readFile(verificationKeyPath, "utf8"));
  if (
    !(await snarkjs.groth16.verify(
      verificationKey,
      proofResult.publicSignals,
      proofResult.proof,
    ))
  ) {
    throw new Error("Generated on-chain risk policy proof failed local verification.");
  }
  return {
    format: "sanctum-onchain-risk-policy-proof-v1",
    policy: "sanctum-provider-risk-at-most-medium-v1",
    policy_id: POLICY_ID,
    assessment_count: ratings.length,
    commitment_root: commitmentRoot,
    proof: proofResult.proof,
    public_signals: proofResult.publicSignals,
    limitations: [
      "This proves only that the committed provider-rating codes are all unknown, low, or medium under this circuit.",
      "It does not prove provider identity, source-report authenticity, address ownership, complete report coverage, or on-chain truth.",
      "The commitment root hides the rating sequence but is not bound to a provider report, addresses, or source reference.",
      "The proof uses Groth16; production use requires an independently conducted trusted setup for this exact circuit.",
    ],
  };
}

async function main() {
  const [inputFile, wasmPath, provingKeyPath, verificationKeyPath, outputFile] =
    process.argv.slice(2);
  if (!inputFile || !wasmPath || !provingKeyPath || !verificationKeyPath || !outputFile) {
    throw new Error(
      "Usage: prove-risk.mjs <ratings-json> <wasm> <proving-key> <verification-key> <output>",
    );
  }
  let input;
  try {
    input = JSON.parse(await readFile(inputFile, "utf8"));
  } catch {
    throw new Error("Risk proof input file cannot be read as JSON.");
  }
  const generated = await proveRiskPolicy(
    input.ratings,
    wasmPath,
    provingKeyPath,
    verificationKeyPath,
  );
  await writeFile(outputFile, `${JSON.stringify(generated, null, 2)}\n`, {
    flag: "wx",
    mode: 0o600,
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(`On-chain risk proof generation failed: ${error.message}`);
    process.exit(1);
  });
}
