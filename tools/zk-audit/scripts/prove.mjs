import { buildPoseidon } from "circomlibjs";
import * as snarkjs from "snarkjs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const BATCH_SIZE = Number(process.env.SANCTUM_ZK_BATCH_SIZE ?? "256");
const TREE_DEPTH = Number(process.env.SANCTUM_ZK_TREE_DEPTH ?? "9");
const POLICY_HASH =
  "1841298221720545410680030688376092580199638229742508812536090285103057017068";
const FIELD_MODULUS =
  21888242871839275222246405745257275088548364400416034343698204186575808495617n;

function field(poseidon, inputs) {
  return poseidon.F.toObject(poseidon(inputs.map((value) => BigInt(value)))).toString();
}

function padEvent() {
  return { event_type: 3, decision: 0, outcome: 0, engine: 0, has_policy_version: 0 };
}

function hashPair(poseidon, left, right) {
  return field(poseidon, [left, right]);
}

function buildLevels(poseidon, leaves, depth) {
  const padded = [...leaves];
  while (padded.length < 2 ** depth) padded.push("0");
  const levels = [padded];
  while (levels.at(-1).length > 1) {
    const previous = levels.at(-1);
    const next = [];
    for (let index = 0; index < previous.length; index += 2) {
      next.push(hashPair(poseidon, previous[index], previous[index + 1]));
    }
    levels.push(next);
  }
  return levels;
}

export async function createProofs(events, wasmPath, provingKeyPath, verificationKeyPath) {
  if (!Array.isArray(events) || events.length === 0 || events.length > 100000) {
    throw new Error("ZK proof input must contain between 1 and 100000 verified audit events.");
  }
  if (
    !Number.isInteger(BATCH_SIZE) ||
    BATCH_SIZE < 1 ||
    (BATCH_SIZE & (BATCH_SIZE - 1)) !== 0 ||
    !Number.isInteger(TREE_DEPTH) ||
    TREE_DEPTH < 1 ||
    TREE_DEPTH > 16
  ) {
    throw new Error("Configured ZK batch size or Merkle depth is invalid.");
  }

  const poseidon = await buildPoseidon();
  const verificationKey = JSON.parse(
    await readFile(verificationKeyPath, "utf8"),
  );
  const normalizedEvents = events.map((event) => {
    const normalized = {
      event_type: Number(event.event_type),
      decision: Number(event.decision),
      outcome: Number(event.outcome),
      engine: Number(event.engine),
      has_policy_version: Number(event.has_policy_version),
      salt: (BigInt(`0x${cryptoRandomHex()}`) % FIELD_MODULUS).toString(),
    };
    if (
      ![0, 1, 2].includes(normalized.event_type) ||
      ![0, 1, 2, 3].includes(normalized.decision) ||
      !Number.isInteger(normalized.outcome) ||
      normalized.outcome < 0 ||
      normalized.outcome > 599 ||
      !Number.isInteger(normalized.engine) ||
      normalized.engine < 0 ||
      normalized.engine > 11 ||
      ![0, 1].includes(normalized.has_policy_version)
    ) {
      throw new Error("ZK proof input contains an invalid normalized audit event.");
    }
    return normalized;
  });

  const chunkCount = Math.ceil(normalizedEvents.length / BATCH_SIZE);
  if (chunkCount > 2 ** TREE_DEPTH) {
    throw new Error("Audit snapshot exceeds the configured chunk-tree capacity.");
  }
  const chunkLeaves = [];
  const chunkInputs = [];
  for (let chunkIndex = 0; chunkIndex < chunkCount; chunkIndex += 1) {
    const chunk = normalizedEvents.slice(
      chunkIndex * BATCH_SIZE,
      (chunkIndex + 1) * BATCH_SIZE,
    );
    const padded = [...chunk];
    while (padded.length < BATCH_SIZE) padded.push(padEvent());
    const leafHashes = padded.map((event) =>
      field(poseidon, [
        event.event_type,
        event.decision,
        event.outcome,
        event.engine,
        event.has_policy_version,
        event.salt ?? 0,
      ]),
    );
    const levels = buildLevels(poseidon, leafHashes, Math.log2(BATCH_SIZE));
    chunkLeaves.push(levels.at(-1)[0]);
    chunkInputs.push({ chunk, eventCount: chunk.length });
  }

  const globalLevels = buildLevels(poseidon, chunkLeaves, TREE_DEPTH);
  const globalRoot = globalLevels.at(-1)[0];
  const proofs = [];
  for (let chunkIndex = 0; chunkIndex < chunkCount; chunkIndex += 1) {
    const { chunk, eventCount } = chunkInputs[chunkIndex];
    const padded = [...chunk];
    while (padded.length < BATCH_SIZE) padded.push(padEvent());
    const witness = {
      globalRoot,
      chunkIndex: String(chunkIndex),
      eventCount: String(eventCount),
      totalRecordCount: String(normalizedEvents.length),
      policyHash: POLICY_HASH,
      eventType: padded.map((event) => String(event.event_type)),
      decision: padded.map((event) => String(event.decision)),
      outcome: padded.map((event) => String(event.outcome)),
      engine: padded.map((event) => String(event.engine)),
      hasPolicyVersion: padded.map((event) => String(event.has_policy_version)),
      salt: padded.map((event) => String(event.salt ?? 0)),
      siblingPath: globalLevels.slice(0, TREE_DEPTH).map((level, depth) => {
        const siblingIndex = (chunkIndex >> depth) ^ 1;
        return level[siblingIndex];
      }),
    };
    const result = await snarkjs.groth16.fullProve(witness, wasmPath, provingKeyPath);
    if (!(await snarkjs.groth16.verify(verificationKey, result.publicSignals, result.proof))) {
      throw new Error(`Generated ZK proof for chunk ${chunkIndex} failed local verification.`);
    }
    proofs.push({ proof: result.proof, public_signals: result.publicSignals });
  }

  return {
    global_root: globalRoot,
    policy_hash: POLICY_HASH,
    batch_size: BATCH_SIZE,
    tree_depth: TREE_DEPTH,
    proofs,
  };
}

function cryptoRandomHex() {
  return [...globalThis.crypto.getRandomValues(new Uint8Array(31))]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

async function main() {
  const [wasmPath, provingKeyPath, verificationKeyPath] = process.argv.slice(2);
  if (!wasmPath || !provingKeyPath || !verificationKeyPath) {
    throw new Error("Usage: prove.mjs <wasm> <proving-key> <verification-key>");
  }
  let source;
  try {
    source = JSON.parse(
      await new Promise((resolve, reject) => {
        let text = "";
        process.stdin.setEncoding("utf8");
        process.stdin.on("data", (chunk) => (text += chunk));
        process.stdin.on("end", () => resolve(text));
        process.stdin.on("error", reject);
      }),
    );
  } catch {
    throw new Error("ZK proof input is not valid JSON.");
  }
  const generated = await createProofs(
    source.events,
    wasmPath,
    provingKeyPath,
    verificationKeyPath,
  );
  process.stdout.write(JSON.stringify(generated));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(`ZK proof generation failed: ${error.stack ?? error.message}`);
    process.exit(1);
  });
}
