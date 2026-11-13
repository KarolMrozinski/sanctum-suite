@0xc0fef00d6c1ea7b5;

using Cxx = import "/capnp/c++.capnp";
$Cxx.namespace("sanctum::runtime");

struct RuntimeEnvelope {
  version @0 :UInt32;
  flowId @1 :Text;
  boundary @2 :TrustBoundary;
  timestamp @3 :UInt64;
  payload @4 :Data;
  attestation @5 :AttestationRecord;
  tags @6 :List(Text);
}

enum TrustBoundary {
  host @0;
  enclave @1;
  tdx @2;
  sevSnp @3;
  cca @4;
  sel4 @5;
}

struct AttestationRecord {
  issuer @0 :Text;
  subject @1 :Text;
  evidenceType @2 :Text;
  quote @3 :Data;
  claims @4 :List(Claim);
}

struct Claim {
  key @0 :Text;
  value @1 :Text;
}
