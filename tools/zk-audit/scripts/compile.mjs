import { cp, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const packageDirectory = path.resolve(scriptDirectory, "..");
const circuitDirectory = path.join(packageDirectory, "circuits");
const circomlibDirectory = path.join(
  packageDirectory,
  "node_modules",
  "circomlib",
  "circuits",
);
const localCircomlibDirectory = path.join(circuitDirectory, "circomlib");
const mode = process.argv[2];
const targets = {
  production: "audit_policy_main",
  test: "audit_policy_test",
};
const circuitName = targets[mode];

if (!circuitName) {
  console.error("Usage: node scripts/compile.mjs <production|test>");
  process.exit(2);
}
if (!existsSync(path.join(circomlibDirectory, "poseidon.circom"))) {
  throw new Error(
    `circomlib circuits are missing from the installed dependency: ${circomlibDirectory}`,
  );
}

await Promise.all([
  rm(path.join(circuitDirectory, `${circuitName}_js`), {
    recursive: true,
    force: true,
  }),
  rm(path.join(circuitDirectory, `${circuitName}.r1cs`), { force: true }),
  rm(path.join(circuitDirectory, `${circuitName}.sym`), { force: true }),
]);

const compiler = path.join(packageDirectory, "node_modules", "circom2", "cli.js");
await rm(localCircomlibDirectory, { recursive: true, force: true });
await cp(circomlibDirectory, localCircomlibDirectory, { recursive: true });

let result;
try {
  result = spawnSync(
    process.execPath,
    [
      compiler,
      `${circuitName}.circom`,
      "--r1cs",
      "--wasm",
      "--sym",
    ],
    {
      cwd: circuitDirectory,
      stdio: "inherit",
    },
  );
} finally {
  await rm(localCircomlibDirectory, { recursive: true, force: true });
}

if (result.error) {
  throw result.error;
}
if (result.status !== 0) {
  process.exit(result.status ?? 1);
}
