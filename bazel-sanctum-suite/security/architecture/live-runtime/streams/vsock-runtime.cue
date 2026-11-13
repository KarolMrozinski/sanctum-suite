package runtime

#TrustDomain: "host" | "enclave" | "tdx" | "sev_snp" | "cca" | "sel4"
#FlowDirection: "ingress" | "egress" | "bidirectional"
#EvidenceMode: "none" | "mTLS" | "SPIRE" | "Keylime" | "Trustee"
#PolicyDecision: "allow" | "deny" | "revalidate"

#VsockSocket: {
  family: "AF_VSOCK"
  cid: int & >= 0
  port: int & >= 0 & <= 65535
  trustDomain: #TrustDomain
  lane: string
  direction: #FlowDirection
  transport: "vsock"
  maxQueueDepth: int & >= 1
  maxLatencyMs: int & >= 1
  payloadSchema: string
  evidenceMode: #EvidenceMode
  attestationRequired: bool
}

#RuntimeEnvelope: {
  version: int & >= 1
  flowId: string
  boundary: #TrustDomain
  timestamp: int
  labels: [...string]
  policy: {
    subject: string
    decision: #PolicyDecision
    issuedAt: int
    ttlSeconds: int & >= 30
    source: string
  }
  payload: {
    type: string
    data: bytes
    schemaRef: string
    tags: [...string]
  }
  attestation: {
    issuer: string
    subject: string
    evidenceType: string
    quote: bytes
    claims: [...{
      key: string
      value: string
    }]
  }
}

#VsockRuntimeConfig: {
  host: #VsockSocket & {
    cid: 2
    port: 5000
    trustDomain: "host"
    lane: "host-to-enclave"
    direction: "bidirectional"
    payloadSchema: "runtime-trust.capnp:RuntimeEnvelope"
    evidenceMode: "SPIRE"
    attestationRequired: true
  }

  enclave: #VsockSocket & {
    cid: 3
    port: 5001
    trustDomain: "tdx"
    lane: "enclave-to-policy"
    direction: "bidirectional"
    payloadSchema: "runtime-trust.capnp:RuntimeEnvelope"
    evidenceMode: "Trustee"
    attestationRequired: true
  }

  policyGateway: #VsockSocket & {
    cid: 4
    port: 5002
    trustDomain: "host"
    lane: "policy-eval"
    direction: "ingress"
    payloadSchema: "runtime-trust.capnp:RuntimeEnvelope"
    evidenceMode: "mTLS"
    attestationRequired: false
  }

  stream: {
    mode: "live"
    realDataReady: true
    contractVersion: "v1"
    bindings: [
      "host-to-enclave",
      "enclave-to-policy",
      "policy-eval",
    ]
  }
}

#VsockRuntimeConfig
