# Zero-knowledge audit policy evidence

Sanctum Suite includes an offline Groth16 proof path for a narrowly defined
audit-evidence rule. It is evidence about fields in a signed WORM audit
snapshot; it is **not** a NIST assessment, NIS2 certification, legal opinion,
or proof that the application executed every operation correctly.

## Rule v1.0

`sanctum-audit-access-policy-v1.0` is an internal, machine-checkable evidence
rule informed by NIST SP 800-53 AC-3, AU-2 and AU-12 and NIS2 Article 21(2)(i).
For every `request_completed` record in a checkpoint, the proof enforces:

- an authorization decision, supported authorization engine, and HTTP outcome
  are present;
- an HTTP 2xx outcome implies the decision is `allow`;
- a `deny` decision has HTTP outcome 403; and
- records attributed to OPA include an authorization policy version.

The rule does not claim that the recorded decision is truthful, that every
request has a matching start/completion pair, or that any wider control family
is satisfied. Other event types are committed to the snapshot but are not
subject to these completion-specific predicates. A failed rule or incomplete
audit record prevents proof generation.

## Snapshot binding and privacy

`sanctum audit-zk-prove` first verifies the checkpoint signature, ordered hash
chain, full version inventory, and every archived record using the existing
offline WORM verifier. It normalizes each record to the fields used by the
circuit, adds a fresh random salt, computes Poseidon commitments and produces
one proof for each batch of up to 256 records. The public proof bundle contains
the commitment root, public inputs, Groth16 proofs, and a signature over a
binding to the exact checkpoint bytes, chain head, record count, policy
identifier, circuit identifier, and verification-key digest. No audit entries,
request identifiers, timestamps, salts, or witness files are included in the
bundle.

The binding signature uses the same RSA-PSS signing identity as the WORM
checkpoint. This makes the relationship between the verified archive and the
private-field commitment explicit and independently checkable, while retaining
a trusted-signer assumption: the SNARK does not verify RSA or re-parse the WORM
archive inside the circuit. Verifiers must trust the checkpoint signer to
validate the archive before signing the binding. The CLI verifier revalidates
the checkpoint and archive before checking the binding signature and every
proof chunk.

The circuit supports checkpoints with 1–100,000 records (up to 391 proofs).
Each proof covers all active records in its batch; the verifier requires
contiguous chunk indices and the exact number of proofs, so omitted chunks are
rejected. Proof generation and verification costs scale with the number of
records. A full-size production snapshot should be benchmarked on the intended
isolated host before operational use.

## Toolchain and local checks

Node.js 22 or later is required for the pinned Circom/snarkjs toolchain. Python
CLI commands also require the Sanctum Suite package to be installed.

```powershell
Set-Location tools\zk-audit
npm ci
npm run compile
npm test
```

`npm test` compiles a reduced circuit and creates a temporary, publicly
deterministic Groth16 ceremony solely to test witness generation, successful
proof verification, and rejection of an invalid 2xx/deny record. Its artifacts
are deleted after the test and must never be used for real evidence.

## Production ceremony and proof commands

Compile the production circuit and conduct an independently operated,
multi-party Powers of Tau and Groth16 phase-2 ceremony. Each participant must
contribute fresh entropy using the organization’s approved procedure; do not
use the test ceremony, deterministic example entropy, or a proving key from
this repository. Retain and independently authenticate the final verification
key and ceremony transcript. The production circuit has 423,074 constraints;
the Powers of Tau circuit power must be at least 19. The final circuit source
hash, compiler/tool versions, ceremony transcript, proving-key digest, and
verification-key digest should be approved and recorded by the operators.

Export the final proving and verification keys to protected locations outside
the repository. The signing private key configured for Sanctum Suite must match
the signer of the checkpoint being proved.

```powershell
sanctum audit-zk-prove C:\secure\audit\checkpoint.json `
  --archive-directory C:\secure\audit\archive `
  --checkpoint-public-key-file C:\secure\keys\sanctum_public.pem `
  --wasm-file tools\zk-audit\circuits\audit_policy_main_js\audit_policy_main.wasm `
  --proving-key-file C:\secure\zk\audit_policy_final.zkey `
  --verification-key-file C:\secure\zk\verification_key.json `
  --output-file C:\secure\audit\checkpoint.zk-proof.json

sanctum audit-zk-verify C:\secure\audit\checkpoint.zk-proof.json `
  --checkpoint-file C:\secure\audit\checkpoint.json `
  --archive-directory C:\secure\audit\archive `
  --checkpoint-public-key-file C:\secure\keys\sanctum_public.pem `
  --verification-key-file C:\secure\zk\verification_key.json
```

Proof bundles and ceremony outputs contain no witness records, but should still
be handled as audit evidence. Keep proving keys protected and offline. A
verifier must obtain the verification key and checkpoint public key through
independent authenticated channels.

## Experimental on-chain provider-rating policy

The separate `sanctum-provider-risk-at-most-medium-v1` circuit demonstrates a
narrow privacy-preserving predicate over a caller-supplied list of 1–8 rating
codes. Rating bands map to `unknown=0`, `low=1`, `medium=2`, `high=3`, and
`severe=4`. The circuit proves that every committed code is below `high`; it
publishes only a Poseidon commitment root, the number of ratings, and the
constant policy identifier. Ratings and random salts remain private.

This is an experimental proof primitive, **not** an attestation of an imported
provider report. The root is not bound to a report digest, provider identity,
assessment addresses/references, completeness claim, or Sanctum case. It cannot
prove that the inputs came from Chainalysis, Elliptic, TRM Labs, or Arkham, nor
that their labels are correct. A user can prove a statement about any chosen
ratings. The proof does not establish that an address is safe, that an
assessment was omitted or included, or that any transaction is lawful. Do not
use the result for a compliance or transaction decision without a separately
authenticated source and a reviewed binding design.

Compile the circuit with the pinned local Circom toolchain:

```powershell
Set-Location tools\zk-audit
npm run compile:risk
```

For a local test only, `npm run compile:risk:test` compiles the same
experimental circuit. `npm test` runs both circuit smoke tests and uses
temporary, publicly deterministic test ceremonies. Those test proving keys
must never be used for production.

The proof helper accepts a JSON input containing rating labels, for example:

```json
{"ratings":["low","medium","unknown"]}
```

After compiling the circuit, preparing an independently operated
Groth16 ceremony for this exact circuit, and storing the resulting files
outside the repository, generate and verify a proof:

```powershell
node scripts\prove-risk.mjs C:\secure\input\rating-bands.json `
  circuits\onchain_risk_policy_js\onchain_risk_policy.wasm `
  C:\secure\zk\onchain_risk_policy_final.zkey `
  C:\secure\zk\onchain_risk_policy_verification_key.json `
  C:\secure\output\rating-policy-proof.json

node scripts\verify-risk.mjs C:\secure\output\rating-policy-proof.json `
  C:\secure\zk\onchain_risk_policy_verification_key.json
```

The helper refuses ratings above `medium` before proving and the circuit also
enforces the same predicate, so an altered helper cannot produce a valid proof
for a higher rating. The bundle includes the public commitment root, count,
policy ID and proof but no labels or salts. Preserve the source material and
its independently authenticated provenance separately if the statement must
be linked to a provider report.

The production circuit has 3,779 nonlinear constraints in the pinned
toolchain build. Operators must verify the circuit source and compiler version,
conduct a fresh, independently reviewed multi-party Groth16 setup with a
Powers of Tau power sufficient for the compiled R1CS, and authenticate the
final verification key out of band. Never use the ephemeral smoke-test
ceremony or keys as real evidence.
