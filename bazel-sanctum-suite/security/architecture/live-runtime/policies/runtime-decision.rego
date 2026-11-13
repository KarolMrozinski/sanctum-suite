package sanctum.runtime.policy

import rego.v1

default allow := false

allow if {
  input.live_mode == true
  input.telemetry_ready == true
  input.boundary in ["host", "enclave", "tdx", "sev_snp", "cca"]
  input.attestation.status == "verified"
}

# Data-agnostic runtime policy; real operational data can be injected at runtime.
# This keeps the evaluation path ready for production evidence without hardcoding payloads.
