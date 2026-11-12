import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
seal = pytest.importorskip("seal")
psycopg = pytest.importorskip("psycopg")
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from typer.testing import CliRunner

from sanctum_suite import main as cli_main
from sanctum_suite.core.privacy_graph import (
    ApacheAGEGraphStore,
    PKCS11ManifestSigner,
    PrivacyGraphError,
    create_fhe_keypair,
    create_private_graph_bundle,
    verify_signed_manifest,
)


CASE_ID = "case-2026-001"
GRAPH = {
    "case_id": CASE_ID,
    "chain": "ethereum",
    "nodes": [
        {
            "id": "address:ethereum:alice",
            "kind": "address",
            "label": "alice",
        },
        {
            "id": "address:ethereum:bob",
            "kind": "address",
            "label": "bob",
        },
    ],
    "edges": [
        {
            "source": "address:ethereum:alice",
            "target": "address:ethereum:bob",
            "relation": "SUBMITS_TO",
            "value_atomic": "42",
        }
    ],
}
SCORES = [
    {"node_id": "address:ethereum:alice", "score": 47},
    {"node_id": "address:ethereum:bob", "score": 18},
]


def _certificate(private_key):
    name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "Sanctum test HSM key")]
    )
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=30)
        )
        .sign(private_key, hashes.SHA256())
    )


class FakeSigner:
    def __init__(self, private_key, cert_fingerprint):
        self._private_key = private_key
        self.certificate_fingerprint = cert_fingerprint

    def sign_manifest(self, payload):
        return self._private_key.sign(
            payload,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )


class FakeAGEStore:
    _graph_name = "sanctum"

    def __init__(self):
        self.imported = None

    def import_graph(self, **kwargs):
        self.imported = kwargs
        return {
            "nodes_persisted": len(kwargs["nodes"]),
            "edges_persisted": len(kwargs["edges"]),
        }


def _write_fhe_keys(tmp_path):
    public_key = tmp_path / "fhe-public.seal"
    private_key = tmp_path / "fhe-private.seal"
    parameters = tmp_path / "fhe-parameters.json"
    report = create_fhe_keypair(
        public_key_path=public_key,
        private_key_path=private_key,
        parameters_path=parameters,
    )
    assert report["private_key_custody"] == "CLIENT_HELD_NOT_STORED_IN_PKCS11"
    return public_key, private_key, parameters


def test_fhe_keygen_cli_and_client_side_decryption(tmp_path):
    public_key = tmp_path / "fhe-public.seal"
    private_key = tmp_path / "fhe-private.seal"
    parameters = tmp_path / "fhe-parameters.json"
    key_result = CliRunner().invoke(
        cli_main.app,
        [
            "fhe-keygen",
            "--public-key-file",
            str(public_key),
            "--private-key-file",
            str(private_key),
            "--parameters-file",
            str(parameters),
        ],
    )
    assert key_result.exit_code == 0, key_result.output

    parameter_values = json.loads(parameters.read_text(encoding="utf-8"))
    params = seal.EncryptionParameters(seal.scheme_type.bfv)
    params.set_poly_modulus_degree(parameter_values["poly_modulus_degree"])
    params.set_coeff_modulus(
        seal.CoeffModulus.BFVDefault(parameter_values["poly_modulus_degree"])
    )
    params.set_plain_modulus(parameter_values["plain_modulus"])
    context = seal.SEALContext(params)
    public = seal.PublicKey()
    public.load(context, str(public_key))
    encryptor = seal.Encryptor(context, public)
    encoder = seal.BatchEncoder(context)
    evaluator = seal.Evaluator(context)
    aggregate = encryptor.encrypt(encoder.encode([12]))
    evaluator.add_inplace(aggregate, encryptor.encrypt(encoder.encode([30])))
    ciphertext = tmp_path / "sum.seal"
    ciphertext.write_bytes(aggregate.to_string())

    decrypt_result = CliRunner().invoke(
        cli_main.app,
        [
            "fhe-decrypt-sum",
            "--parameters-file",
            str(parameters),
            "--private-key-file",
            str(private_key),
            "--ciphertext-file",
            str(ciphertext),
        ],
    )

    assert decrypt_result.exit_code == 0, decrypt_result.output
    assert json.loads(decrypt_result.stdout)["aggregate_score"] == 42
    assert private_key.exists()
    assert public_key.exists()


def test_private_graph_bundle_encrypts_scores_signs_manifest_and_verifies(
    tmp_path,
):
    graph_path = tmp_path / "graph.json"
    scores_path = tmp_path / "scores.json"
    graph_path.write_text(json.dumps(GRAPH), encoding="utf-8")
    scores_path.write_text(json.dumps(SCORES), encoding="utf-8")
    public_key, private_key, parameters = _write_fhe_keys(tmp_path)
    hsm_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    certificate = _certificate(hsm_key)
    certificate_path = tmp_path / "hsm-certificate.pem"
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    certificate_fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
    age_store = FakeAGEStore()
    output = tmp_path / "private-graph-bundle"

    report = create_private_graph_bundle(
        graph_path=graph_path,
        scores_path=scores_path,
        case_id=CASE_ID,
        public_key_path=public_key,
        parameters_path=parameters,
        output_directory=output,
        graph_store=age_store,
        signer=FakeSigner(hsm_key, certificate_fingerprint),
    )

    manifest_path = output / "manifest.json"
    signature_path = output / "manifest.sig"
    ciphertext_path = output / "aggregate.seal"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert report["status"] == "PRIVATE_GRAPH_IMPORTED"
    assert report["fhe_key_custody"] == "CLIENT_HELD_NOT_STORED_IN_PKCS11"
    assert report["graph_nodes"] == 2
    assert report["graph_edges"] == 1
    assert manifest["fhe_score_count"] == 2
    assert manifest["signer_certificate_sha256"] == certificate_fingerprint
    assert {"scores", "score_values", "node_scores"}.isdisjoint(manifest)
    assert all("score" not in node for node in age_store.imported["nodes"])
    assert all(
        isinstance(value, bytes)
        for value in age_store.imported["encrypted_scores"].values()
    )
    assert set(age_store.imported["encrypted_scores"]) == {
        item["node_id"] for item in SCORES
    }

    verified = verify_signed_manifest(
        manifest_path=manifest_path,
        signature_path=signature_path,
        ciphertext_path=ciphertext_path,
        certificate_path=certificate_path,
    )
    assert verified["status"] == "HSM_SIGNATURE_VERIFIED"
    assert verified["fhe_aggregate_ciphertext_sha256"] == hashlib.sha256(
        ciphertext_path.read_bytes()
    ).hexdigest()

    ciphertext_bytes = ciphertext_path.read_bytes()
    ciphertext_path.write_bytes(b"modified")
    with pytest.raises(PrivacyGraphError, match="digest does not match"):
        verify_signed_manifest(
            manifest_path=manifest_path,
            signature_path=signature_path,
            ciphertext_path=ciphertext_path,
            certificate_path=certificate_path,
        )

    bad_decrypt = CliRunner().invoke(
        cli_main.app,
        [
            "fhe-decrypt-sum",
            "--parameters-file",
            str(parameters),
            "--private-key-file",
            str(private_key),
            "--ciphertext-file",
            str(ciphertext_path),
        ],
    )
    assert bad_decrypt.exit_code != 0
    assert "Could not decrypt" in bad_decrypt.output

    ciphertext_path.write_bytes(ciphertext_bytes)
    decrypt_result = CliRunner().invoke(
        cli_main.app,
        [
            "fhe-decrypt-sum",
            "--parameters-file",
            str(parameters),
            "--private-key-file",
            str(private_key),
            "--ciphertext-file",
            str(output / "aggregate.seal"),
        ],
    )
    assert decrypt_result.exit_code == 0, decrypt_result.output
    assert json.loads(decrypt_result.stdout)["aggregate_score"] == 65


def test_age_query_uses_parameters_for_graph_data_and_rejects_remote_plaintext(
    tmp_path, monkeypatch
):
    dsn_file = tmp_path / "age-dsn"
    dsn_file.write_text("host=localhost dbname=sanctum", encoding="utf-8")
    statements = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, query, params=None):
            statements.append((query, params))

        def fetchone(self):
            query, _ = statements[-1]
            if "ag_catalog.ag_graph" in query:
                return ("sanctum",)
            return ("persisted",)

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(
        psycopg,
        "connect",
        lambda dsn, connect_timeout: Connection(),
    )
    store = ApacheAGEGraphStore(dsn_file=dsn_file, graph_name="sanctum")
    result = store.import_graph(
        case_id=CASE_ID,
        manifest_id="f" * 64,
        nodes=GRAPH["nodes"],
        edges=GRAPH["edges"],
        encrypted_scores={"address:ethereum:alice": b"encrypted-score"},
    )

    assert result == {"nodes_persisted": 2, "edges_persisted": 1}
    cypher_statements = [
        (query, params)
        for query, params in statements
        if "ag_catalog.cypher" in query
    ]
    assert len(cypher_statements) == 3
    assert all("%s" in query for query, _ in cypher_statements)
    assert all(
        "alice" not in query and "SUBMITS_TO" not in query
        for query, _ in cypher_statements
    )
    assert json.loads(cypher_statements[0][1][1])["case_id"] == CASE_ID
    assert json.loads(cypher_statements[0][1][1])["manifest_id"] == "f" * 64
    assert (
        json.loads(cypher_statements[0][1][1])["properties"]["encrypted_score"]
        == "ZW5jcnlwdGVkLXNjb3Jl"
    )
    assert "case_id: $case_id" in cypher_statements[0][0]
    assert "manifest_id: $manifest_id" in cypher_statements[0][0]
    assert json.loads(cypher_statements[-1][1][1])["edge_id"]
    assert b"encrypted-score" not in str(cypher_statements).encode()

    remote_dsn = tmp_path / "remote-dsn"
    remote_dsn.write_text(
        "host=graph.internal dbname=sanctum sslmode=require",
        encoding="utf-8",
    )
    with pytest.raises(PrivacyGraphError, match="sslmode=verify-full"):
        ApacheAGEGraphStore(dsn_file=remote_dsn)


def test_pkcs11_signer_uses_external_library_and_checks_hsm_certificate(
    tmp_path, monkeypatch
):
    hsm_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    certificate = _certificate(hsm_key)
    certificate_path = tmp_path / "hsm-certificate.pem"
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    pin_file = tmp_path / "hsm-pin"
    pin_file.write_text("test-pin\n", encoding="utf-8")
    calls = []

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def get_key(self, **kwargs):
            assert kwargs["label"] == "manifest-key"
            return SimpleNamespace(
                sign=lambda data, mechanism: (
                    calls.append((data, mechanism))
                    or hsm_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
                )
            )

    class Token:
        def open(self, *, user_pin):
            assert user_pin == "test-pin"
            return Session()

    fake_pkcs11 = SimpleNamespace(
        lib=lambda path: SimpleNamespace(
            get_token=lambda *, token_label: Token()
        ),
        KeyType=SimpleNamespace(RSA="RSA"),
        ObjectClass=SimpleNamespace(PRIVATE_KEY="PRIVATE_KEY"),
        Mechanism=SimpleNamespace(SHA256_RSA_PKCS="SHA256_RSA_PKCS"),
        PKCS11Error=RuntimeError,
    )
    monkeypatch.setitem(sys.modules, "pkcs11", fake_pkcs11)
    signer = PKCS11ManifestSigner(
        module_path="vendor-pkcs11.dll",
        token_label="sanctum",
        key_label="manifest-key",
        pin_file=pin_file,
        certificate_file=certificate_path,
    )

    payload = b"canonical manifest"
    signature = signer.sign_manifest(payload)
    certificate.public_key().verify(
        signature, payload, padding.PKCS1v15(), hashes.SHA256()
    )
    assert calls == [(payload, "SHA256_RSA_PKCS")]
    assert signer.certificate_fingerprint == certificate.fingerprint(
        hashes.SHA256()
    ).hex()


@pytest.mark.parametrize(
    "scores",
    [
        [{"node_id": "address:ethereum:alice", "score": True}],
        [{"node_id": "address:ethereum:missing", "score": 1}],
        [{"node_id": "address:ethereum:alice", "score": 1.5}],
        [{"node_id": "address:ethereum:alice", "score": 1001}],
    ],
)
def test_private_graph_rejects_scores_that_are_not_bounded_integers(scores):
    from sanctum_suite.core.privacy_graph import _validate_scores, _validate_graph

    nodes, _ = _validate_graph(GRAPH, CASE_ID)
    with pytest.raises(PrivacyGraphError):
        _validate_scores(scores, nodes)


def test_private_graph_rejects_invalid_case_ids():
    from sanctum_suite.core.privacy_graph import _validate_graph

    with pytest.raises(PrivacyGraphError, match="requested case_id"):
        _validate_graph(GRAPH, "case id with spaces")
