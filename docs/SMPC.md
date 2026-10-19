# SMPC: three-party private integer aggregation (experimental)

[`MPyC`](https://mpyc.readthedocs.io/en/latest/) is an optional research
library. `sanctum smpc-aggregate-demo` runs three separate local MPyC processes to
compute the sum of three bounded integer inputs and whether that sum reaches
a public threshold. MPyC secret-shares each participant's input and performs
the addition and comparison on secret-shared values. Only the sum and
threshold bit are revealed by the MPC operation; no individual input is
included in CLI output.

This is a **local demonstration**, not an inter-organization service. The
coordinator launches all three participant processes on one machine and can
access their input-file paths; local processes communicate only over loopback.
The demo uses three parties and Shamir threshold `t=1` in a **semi-honest**
model: participants are assumed to follow the protocol, although up to one
share may be observed. It does not protect against active/malicious parties,
host administrators, compromised operating systems, denial of service,
network traffic analysis outside loopback, or unsafe participant binaries.
Do not use this prototype for production, regulated or classified data.

## Install

Install the optional MPyC dependency:

```powershell
python -m pip install ".[smpc]"
```

## Inputs

Each participant prepares a separate JSON file containing only its own
non-negative integer contribution, from 0 to 1,000,000:

```json
{"value": 120}
```

Input files are limited to 16 KiB. The controller checks only that the files
exist and are size-bounded; each participant process parses its own file.
Never point multiple parties at the same input file.

## Run the local demo

```powershell
sanctum smpc-aggregate-demo `
  --party-0-input-file C:\secure\demo\party-0.json `
  --party-1-input-file C:\secure\demo\party-1.json `
  --party-2-input-file C:\secure\demo\party-2.json `
  --decision-threshold 700
```

The command requires three distinct input files and a threshold from 0 to
3,000,000. It starts three MPyC party processes bound to loopback ports,
requires all three to complete, and fails closed on a participant error or
timeout. The result contains the aggregate integer and a boolean indicating
whether it meets the public threshold. All parties participating in this
protocol learn those outputs; repeated runs may reveal information, so do not
allow arbitrary/adaptive threshold queries over the same inputs.

## Security and operational limits

- MPyC is an optional research/engineering dependency. This demo does not
  independently audit its cryptographic implementation or runtime.
- The local harness is useful for API and protocol experiments only. It does
  not provide separate administrative domains, authenticated remote parties,
  TLS certificates, participant enrollment, availability, or a production
  deployment lifecycle.
- There is no active-security guarantee: a participant may deviate from the
  protocol or submit an invalid value. The input schema enforces local integer
  bounds, but does not prove an input's provenance or correctness.
- The threshold bit is an intentional release of information in addition to
  the sum. The implementation does not apply differential privacy, query
  budgets, or minimum cohort sizes.
- No per-party values, input paths, or identities are emitted in the result.
  The output is not bound to an audit checkpoint or written to Fabric.
- The feature does not replace the separate Microsoft SEAL FHE workflow.
  SMPC distributes participation and trust across protocol parties; FHE
  encrypts inputs for computation without requiring all parties to be online
  in the same protocol session.

Before any remote/production use, select an actively reviewed protocol and
threat model, authenticate and encrypt inter-party channels, define input
validation/provenance and output governance, test process/network failure
recovery, and obtain independent cryptographic and operational review.
