from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


_MAX_GRAPH_NODES = 5_000
_MAX_GRAPH_EDGES = 10_000
_MAX_SCORE_COUNT = 5_000
_MAX_SCORE = 1_000
_POLY_MODULUS_DEGREE = 8_192
_PLAIN_MODULUS_BITS = 30
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_GRAPH_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
_SCORE_FIELDS = {"node_id", "score"}
_RESERVED_NODE_FIELDS = {"id", "case_id", "manifest_id", "encrypted_score"}
_RESERVED_EDGE_FIELDS = {"case_id", "manifest_id", "relation"}


class PrivacyGraphError(ValueError):
    """Raised when a private graph import cannot safely complete."""


class FHEAcceleratorBackend(Protocol):
    """Adapter contract for an independently validated accelerator implementation."""

    backend_name: str

    def encrypt_and_aggregate(
        self,
        *,
        public_key_path: Path,
        parameters_path: Path,
        scores: list[dict[str, Any]],
    ) -> tuple[list[tuple[str, bytes]], bytes, dict[str, Any]]: ...


def fhe_accelerator_capabilities() -> dict[str, Any]:
    """Report installed FHE support and tooling without claiming device/offload support."""
    return {
        "status": "CAPABILITY_REPORT_ONLY",
        "cpu_backend": {
            "name": "Microsoft SEAL BFV",
            "python_binding_available": importlib.util.find_spec("seal") is not None,
            "execution": "CPU",
        },
        "accelerator_backends": {
            "gpu": {
                "status": "NOT_IMPLEMENTED",
                "runtime_tool_present": any(
                    shutil.which(tool) is not None
                    for tool in ("nvidia-smi", "rocminfo")
                ),
            },
            "fpga": {
                "status": "NOT_IMPLEMENTED",
                "runtime_tool_present": any(
                    shutil.which(tool) is not None
                    for tool in ("xrt-smi", "xbutil")
                ),
            },
        },
        "limitations": (
            "Runtime tools do not prove an attached device, secure isolation, "
            "or FHE acceleration. Microsoft SEAL in this package uses the CPU; "
            "no GPU/FPGA backend is bundled or automatically selected."
        ),
    }


def _read_limited(path: Path, label: str, *, maximum: int = 32 * 1024 * 1024) -> bytes:
    try:
        with path.open("rb") as source:
            raw = source.read(maximum + 1)
    except OSError as error:
        raise PrivacyGraphError(f"Cannot read {label}: {error}") from error
    if len(raw) > maximum:
        raise PrivacyGraphError(
            f"{label} must not exceed {maximum // (1024 * 1024)} MiB"
        )
    return raw


def _read_json(
    path: Path,
    label: str,
    *,
    maximum: int = 32 * 1024 * 1024,
) -> tuple[bytes, Any]:
    raw = _read_limited(path, label, maximum=maximum)
    try:
        return raw, json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PrivacyGraphError(f"{label} must contain valid UTF-8 JSON") from error


def _seal():
    try:
        import seal
    except ImportError as error:
        raise PrivacyGraphError(
            "FHE support requires the optional sanctum-suite[privacy-graph] extra"
        ) from error
    return seal


def _build_context(seal: Any, plain_modulus: int):
    parameters = seal.EncryptionParameters(seal.scheme_type.bfv)
    parameters.set_poly_modulus_degree(_POLY_MODULUS_DEGREE)
    parameters.set_coeff_modulus(
        seal.CoeffModulus.BFVDefault(_POLY_MODULUS_DEGREE)
    )
    parameters.set_plain_modulus(plain_modulus)
    context = seal.SEALContext(parameters)
    if not context.parameters_set():
        raise PrivacyGraphError("Microsoft SEAL rejected the configured BFV parameters")
    return parameters, context


def create_fhe_keypair(
    *,
    public_key_path: Path,
    private_key_path: Path,
    parameters_path: Path,
) -> dict[str, Any]:
    seal = _seal()
    paths = {path.resolve() for path in (public_key_path, private_key_path, parameters_path)}
    if len(paths) != 3:
        raise PrivacyGraphError("FHE public key, private key, and parameters must be separate files")
    if any(path.exists() for path in paths):
        raise PrivacyGraphError("FHE key output files must not already exist")
    if any(not path.parent.is_dir() for path in (public_key_path, private_key_path, parameters_path)):
        raise PrivacyGraphError("FHE key output parent directories must already exist")

    parameters, context = _build_context(
        seal,
        int(seal.PlainModulus.Batching(_POLY_MODULUS_DEGREE, _PLAIN_MODULUS_BITS).value()),
    )
    key_generator = seal.KeyGenerator(context)
    public_key = seal.PublicKey()
    key_generator.create_public_key(public_key)
    secret_key = key_generator.secret_key()

    temporary_paths: list[tuple[Path, Path]] = []
    try:
        for target in (public_key_path, private_key_path, parameters_path):
            with tempfile.NamedTemporaryFile(
                prefix=f".{target.name}.",
                suffix=".tmp",
                dir=target.parent,
                delete=False,
            ) as temporary:
                temporary_paths.append((Path(temporary.name), target))
        public_key.save(str(temporary_paths[0][0]))
        secret_key.save(str(temporary_paths[1][0]))
        if os.name != "nt":
            temporary_paths[1][0].chmod(0o600)
        metadata = {
            "scheme": "BFV",
            "poly_modulus_degree": _POLY_MODULUS_DEGREE,
            "plain_modulus": int(parameters.plain_modulus().value()),
            "security_level": "128-bit classical (SEAL tc128)",
            "private_key_custody": "CLIENT_HELD_NOT_STORED_IN_PKCS11",
        }
        temporary_paths[2][0].write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        for source, target in temporary_paths:
            os.replace(source, target)
    except (OSError, RuntimeError) as error:
        for source, _ in temporary_paths:
            source.unlink(missing_ok=True)
        for target in (public_key_path, private_key_path, parameters_path):
            target.unlink(missing_ok=True)
        raise PrivacyGraphError(f"Could not create FHE key files: {error}") from error

    return {
        "status": "FHE_KEYPAIR_CREATED",
        "scheme": "Microsoft SEAL BFV",
        "public_key": str(public_key_path),
        "private_key": str(private_key_path),
        "parameters": str(parameters_path),
        "private_key_custody": "CLIENT_HELD_NOT_STORED_IN_PKCS11",
        "limitations": (
            "The private BFV key is stored as a client-held file. PKCS#11 HSMs "
            "do not perform these BFV operations; the HSM integration is used "
            "separately to sign the graph manifest."
        ),
    }


def _load_fhe_context(parameters_path: Path):
    seal = _seal()
    _, metadata = _read_json(parameters_path, "FHE parameter file")
    if (
        not isinstance(metadata, dict)
        or metadata.get("scheme") != "BFV"
        or metadata.get("poly_modulus_degree") != _POLY_MODULUS_DEGREE
        or metadata.get("security_level") != "128-bit classical (SEAL tc128)"
        or not isinstance(metadata.get("plain_modulus"), int)
        or isinstance(metadata.get("plain_modulus"), bool)
    ):
        raise PrivacyGraphError("FHE parameter file has an unsupported configuration")
    try:
        _, context = _build_context(seal, metadata["plain_modulus"])
    except (RuntimeError, ValueError, TypeError) as error:
        raise PrivacyGraphError("FHE parameter file is invalid") from error
    return seal, context, metadata


def decrypt_fhe_sum(
    *,
    parameters_path: Path,
    private_key_path: Path,
    ciphertext_path: Path,
) -> dict[str, Any]:
    seal, context, metadata = _load_fhe_context(parameters_path)
    if not private_key_path.is_file():
        raise PrivacyGraphError("Client-held FHE private key file does not exist")
    ciphertext_bytes = _read_limited(
        ciphertext_path, "FHE aggregate ciphertext", maximum=64 * 1024 * 1024
    )
    try:
        secret_key = seal.SecretKey()
        secret_key.load(context, str(private_key_path))
        decryptor = seal.Decryptor(context, secret_key)
        encrypted_sum = context.from_cipher_str(ciphertext_bytes)
        plaintext = decryptor.decrypt(encrypted_sum)
        total = int(seal.BatchEncoder(context).decode(plaintext)[0])
        if not 0 <= total <= _MAX_SCORE * _MAX_SCORE_COUNT:
            raise PrivacyGraphError(
                "Decrypted aggregate is outside the supported score range"
            )
    except PrivacyGraphError:
        raise
    except (OSError, RuntimeError, ValueError, TypeError, IndexError) as error:
        raise PrivacyGraphError(
            "Could not decrypt the supplied aggregate with this client-held key"
        ) from error
    return {
        "status": "FHE_AGGREGATE_DECRYPTED",
        "scheme": "Microsoft SEAL BFV",
        "aggregate_score": total,
        "private_key_custody": "CLIENT_HELD_NOT_STORED_IN_PKCS11",
        "limitations": (
            "The decrypted sum is an arithmetic result over encrypted integer "
            "inputs; it is not an independently validated score, risk verdict, "
            "attribution, or compliance determination."
        ),
        "parameters": metadata,
    }


def _validate_graph(graph: Any, case_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if (
        not isinstance(case_id, str)
        or not _IDENTIFIER.fullmatch(case_id)
        or not isinstance(graph, dict)
        or graph.get("case_id") != case_id
    ):
        raise PrivacyGraphError("Graph JSON must belong to the requested case_id")
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= _MAX_GRAPH_NODES:
        raise PrivacyGraphError(f"Graph nodes must contain 1 to {_MAX_GRAPH_NODES} entries")
    if not isinstance(edges, list) or len(edges) > _MAX_GRAPH_EDGES:
        raise PrivacyGraphError(f"Graph edges must contain at most {_MAX_GRAPH_EDGES} entries")
    node_ids: set[str] = set()
    for node in nodes:
        if (
            not isinstance(node, dict)
            or not isinstance(node.get("id"), str)
            or not _IDENTIFIER.fullmatch(node["id"])
        ):
            raise PrivacyGraphError("Graph node IDs must be structured identifiers")
        if node["id"] in node_ids:
            raise PrivacyGraphError("Graph contains duplicate node IDs")
        node_ids.add(node["id"])
        if any(
            not isinstance(key, str)
            or not _IDENTIFIER.fullmatch(key)
            or key in _RESERVED_NODE_FIELDS
            for key, value in node.items()
            if key != "id"
        ):
            raise PrivacyGraphError("Graph node contains a reserved or invalid property")
        try:
            json.dumps(node, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise PrivacyGraphError("Graph node properties must be finite JSON values") from error
    for edge in edges:
        if (
            not isinstance(edge, dict)
            or edge.get("source") not in node_ids
            or edge.get("target") not in node_ids
            or not isinstance(edge.get("relation"), str)
            or not _IDENTIFIER.fullmatch(edge["relation"])
        ):
            raise PrivacyGraphError("Graph edge endpoints or relation are invalid")
        if any(
            not isinstance(key, str)
            or not _IDENTIFIER.fullmatch(key)
            or key in _RESERVED_EDGE_FIELDS
            for key in edge
            if key not in {"source", "target", "relation"}
        ):
            raise PrivacyGraphError("Graph edge contains a reserved or invalid property")
        try:
            json.dumps(edge, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise PrivacyGraphError("Graph edge properties must be finite JSON values") from error
    return nodes, edges


def _validate_scores(
    raw_scores: Any, nodes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not isinstance(raw_scores, list) or not 1 <= len(raw_scores) <= _MAX_SCORE_COUNT:
        raise PrivacyGraphError(
            f"Scores must contain 1 to {_MAX_SCORE_COUNT} entries"
        )
    node_ids = {node["id"] for node in nodes}
    seen: set[str] = set()
    for entry in raw_scores:
        if (
            not isinstance(entry, dict)
            or set(entry) != _SCORE_FIELDS
            or not isinstance(entry.get("node_id"), str)
            or entry["node_id"] not in node_ids
            or entry["node_id"] in seen
            or not isinstance(entry.get("score"), int)
            or isinstance(entry["score"], bool)
            or not 0 <= entry["score"] <= _MAX_SCORE
        ):
            raise PrivacyGraphError(
                "Each score must have a unique graph node_id and an integer "
                f"score from 0 to {_MAX_SCORE}"
            )
        seen.add(entry["node_id"])
    return raw_scores


def _encrypt_scores(
    *,
    public_key_path: Path,
    parameters_path: Path,
    scores: list[dict[str, Any]],
    accelerator_backend: FHEAcceleratorBackend | None = None,
):
    if accelerator_backend is not None:
        result = accelerator_backend.encrypt_and_aggregate(
            public_key_path=public_key_path,
            parameters_path=parameters_path,
            scores=scores,
        )
        if (
            not isinstance(result, tuple)
            or len(result) != 3
            or not isinstance(result[0], list)
            or not isinstance(result[1], bytes)
            or not isinstance(result[2], dict)
            or not isinstance(accelerator_backend.backend_name, str)
            or not accelerator_backend.backend_name
        ):
            raise PrivacyGraphError("FHE accelerator backend returned an invalid result")
        encrypted_scores, aggregate_bytes, metadata = result
        try:
            json.dumps(metadata, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise PrivacyGraphError(
                "FHE accelerator backend returned non-JSON metadata"
            ) from error
        if (
            len(encrypted_scores) != len(scores)
            or any(
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not isinstance(item[1], bytes)
                or not item[1]
                for item in encrypted_scores
            )
            or not aggregate_bytes
            or len({node_id for node_id, _ in encrypted_scores})
            != len(encrypted_scores)
            or {node_id for node_id, _ in encrypted_scores}
            != {entry["node_id"] for entry in scores}
        ):
            raise PrivacyGraphError(
                "FHE accelerator backend did not return one ciphertext per score"
            )
        return encrypted_scores, aggregate_bytes, {
            **metadata,
            "execution_backend": accelerator_backend.backend_name,
        }
    seal, context, metadata = _load_fhe_context(parameters_path)
    if not public_key_path.is_file():
        raise PrivacyGraphError("FHE public key file does not exist")
    try:
        public_key = seal.PublicKey()
        public_key.load(context, str(public_key_path))
        encryptor = seal.Encryptor(context, public_key)
        encoder = seal.BatchEncoder(context)
        evaluator = seal.Evaluator(context)
        encrypted: list[tuple[str, bytes]] = []
        encrypted_sum = None
        for entry in scores:
            plaintext = encoder.encode([entry["score"]])
            ciphertext = encryptor.encrypt(plaintext)
            ciphertext_bytes = ciphertext.to_string()
            if not isinstance(ciphertext_bytes, bytes):
                raise PrivacyGraphError("SEAL returned an invalid ciphertext encoding")
            encrypted.append((entry["node_id"], ciphertext_bytes))
            if encrypted_sum is None:
                encrypted_sum = context.from_cipher_str(ciphertext_bytes)
            else:
                evaluator.add_inplace(
                    encrypted_sum,
                    context.from_cipher_str(ciphertext_bytes),
                )
        if encrypted_sum is None:
            raise PrivacyGraphError("At least one encrypted score is required")
        aggregate_bytes = encrypted_sum.to_string()
        if not isinstance(aggregate_bytes, bytes):
            raise PrivacyGraphError("SEAL returned an invalid aggregate ciphertext")
    except PrivacyGraphError:
        raise
    except (OSError, RuntimeError, ValueError, TypeError) as error:
        raise PrivacyGraphError(
            "Could not encrypt and aggregate graph scores with Microsoft SEAL"
        ) from error
    return encrypted, aggregate_bytes, {
        **metadata,
        "execution_backend": "microsoft-seal-cpu",
    }


class ApacheAGEGraphStore:
    """Persists a case-scoped graph and encrypted score ciphertexts in Apache AGE."""

    def __init__(
        self,
        *,
        dsn_file: Path,
        graph_name: str = "sanctum",
    ) -> None:
        if not _GRAPH_NAME.fullmatch(graph_name):
            raise PrivacyGraphError("Apache AGE graph name is invalid")
        try:
            dsn = dsn_file.read_text(encoding="utf-8").strip()
        except OSError as error:
            raise PrivacyGraphError("Cannot read Apache AGE connection secret file") from error
        if not dsn or "\n" in dsn or "\r" in dsn:
            raise PrivacyGraphError("Apache AGE connection secret file is invalid")
        try:
            from psycopg.conninfo import conninfo_to_dict

            connection_info = conninfo_to_dict(dsn)
        except (ImportError, ValueError) as error:
            raise PrivacyGraphError(
                "Apache AGE connection string is invalid or psycopg is unavailable"
            ) from error
        hosts = connection_info.get("host", "localhost").split(",")
        remote_hosts = [
            host.strip()
            for host in hosts
            if host.strip().lower() not in {"", "localhost", "127.0.0.1", "::1"}
            and not host.strip().startswith("/")
        ]
        if remote_hosts:
            if connection_info.get("sslmode") != "verify-full":
                raise PrivacyGraphError(
                    "Remote Apache AGE connections require sslmode=verify-full"
                )
            root_certificate = connection_info.get("sslrootcert", "")
            if not root_certificate or not Path(root_certificate).expanduser().is_file():
                raise PrivacyGraphError(
                    "Remote Apache AGE connections require an existing sslrootcert"
                )
        self._dsn = dsn
        self._graph_name = graph_name

    def import_graph(
        self,
        *,
        case_id: str,
        manifest_id: str,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        encrypted_scores: dict[str, bytes],
    ) -> dict[str, int]:
        try:
            import psycopg
        except ImportError as error:
            raise PrivacyGraphError(
                "Apache AGE support requires the optional sanctum-suite[privacy-graph] extra"
            ) from error
        try:
            with psycopg.connect(self._dsn, connect_timeout=5) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("LOAD 'age'")
                    cursor.execute('SET search_path = ag_catalog, "$user", public')
                    cursor.execute(
                        "SELECT name FROM ag_catalog.ag_graph WHERE name = %s",
                        (self._graph_name,),
                    )
                    if cursor.fetchone() is None:
                        cursor.execute(
                            "SELECT ag_catalog.create_graph(%s)",
                            (self._graph_name,),
                        )
                    for node in nodes:
                        properties = {
                            key: value for key, value in node.items() if key != "id"
                        }
                        properties.update(
                            {"case_id": case_id, "manifest_id": manifest_id}
                        )
                        encrypted = encrypted_scores.get(node["id"])
                        if encrypted is not None:
                            properties["encrypted_score"] = base64.b64encode(
                                encrypted
                            ).decode("ascii")
                        parameters = json.dumps(
                            {
                                "id": node["id"],
                                "case_id": case_id,
                                "manifest_id": manifest_id,
                                "properties": properties,
                            },
                            separators=(",", ":"),
                            allow_nan=False,
                        )
                        cursor.execute(
                            """
                            SELECT * FROM ag_catalog.cypher(
                                %s,
                                $$ MERGE (n:SanctumNode {
                                       id: $id,
                                       case_id: $case_id,
                                       manifest_id: $manifest_id
                                   })
                                   SET n += $properties
                                   RETURN n.id $$,
                                %s::agtype
                            ) AS (node_id agtype)
                            """,
                            (self._graph_name, parameters),
                        )
                        if cursor.fetchone() is None:
                            raise PrivacyGraphError(
                                "Apache AGE did not persist a graph node"
                            )
                    for edge_index, edge in enumerate(edges):
                        properties = {
                            key: value
                            for key, value in edge.items()
                            if key not in {"source", "target", "relation"}
                        }
                        properties.update(
                            {
                                "case_id": case_id,
                                "manifest_id": manifest_id,
                                "relation": edge["relation"],
                            }
                        )
                        parameters = json.dumps(
                            {
                                "source_id": edge["source"],
                                "target_id": edge["target"],
                                "case_id": case_id,
                                "manifest_id": manifest_id,
                                "relation": edge["relation"],
                                "edge_id": hashlib.sha256(
                                    json.dumps(
                                        [edge_index, edge],
                                        sort_keys=True,
                                        separators=(",", ":"),
                                        ensure_ascii=True,
                                        allow_nan=False,
                                    ).encode("utf-8")
                                ).hexdigest(),
                                "properties": properties,
                            },
                            separators=(",", ":"),
                            allow_nan=False,
                        )
                        cursor.execute(
                            """
                            SELECT * FROM ag_catalog.cypher(
                                %s,
                                $$ MATCH (s:SanctumNode {
                                       id: $source_id,
                                       case_id: $case_id,
                                       manifest_id: $manifest_id
                                   })
                                   MATCH (t:SanctumNode {
                                       id: $target_id,
                                       case_id: $case_id,
                                       manifest_id: $manifest_id
                                   })
                                   MERGE (s)-[r:SANCTUM_RELATION {
                                       manifest_id: $manifest_id,
                                       relation: $relation,
                                       edge_id: $edge_id
                                   }]->(t)
                                   SET r += $properties
                                   RETURN id(r) $$,
                                %s::agtype
                            ) AS (edge_id agtype)
                            """,
                            (self._graph_name, parameters),
                        )
                        if cursor.fetchone() is None:
                            raise PrivacyGraphError(
                                "Apache AGE did not persist a graph relation"
                            )
            return {"nodes_persisted": len(nodes), "edges_persisted": len(edges)}
        except PrivacyGraphError:
            raise
        except psycopg.Error as error:
            raise PrivacyGraphError(
                "Apache AGE graph import failed; database credentials and query "
                "details were withheld"
            ) from error


class PKCS11ManifestSigner:
    """Signs canonical manifest bytes with an HSM RSA key via PKCS#11."""

    def __init__(
        self,
        *,
        module_path: str,
        token_label: str,
        key_label: str,
        pin_file: Path,
        certificate_file: Path,
    ) -> None:
        if not module_path or not token_label or not key_label:
            raise PrivacyGraphError(
                "PKCS#11 module, token label, and private-key label are required"
            )
        try:
            pin_bytes = _read_limited(
                pin_file, "PKCS#11 PIN secret", maximum=4096
            )
            self._pin = pin_bytes.decode("utf-8").strip()
        except UnicodeDecodeError as error:
            raise PrivacyGraphError("PKCS#11 PIN secret file must contain UTF-8") from error
        if not self._pin or "\n" in self._pin or "\r" in self._pin:
            raise PrivacyGraphError("PKCS#11 PIN secret file is invalid")
        self._module_path = module_path
        self._token_label = token_label
        self._key_label = key_label
        self._certificate = _read_limited(
            certificate_file, "HSM signer certificate", maximum=1024 * 1024
        )
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa

            try:
                certificate = x509.load_pem_x509_certificate(self._certificate)
            except ValueError:
                certificate = x509.load_der_x509_certificate(self._certificate)
            public_key = certificate.public_key()
            if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 2048:
                raise PrivacyGraphError(
                    "HSM manifest signing requires an RSA certificate of at least 2048 bits"
                )
            self._certificate_fingerprint = certificate.fingerprint(
                hashes.SHA256()
            ).hex()
            self._public_key = public_key
        except PrivacyGraphError:
            raise
        except (ValueError, TypeError) as error:
            raise PrivacyGraphError("HSM signer certificate is invalid") from error

    @property
    def certificate_fingerprint(self) -> str:
        return self._certificate_fingerprint

    def sign_manifest(self, manifest_bytes: bytes) -> bytes:
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            import pkcs11
        except ImportError as error:
            raise PrivacyGraphError(
                "PKCS#11 support requires the optional sanctum-suite[privacy-graph] extra"
            ) from error
        try:
            pkcs11_library = pkcs11.lib(self._module_path)
            token = pkcs11_library.get_token(token_label=self._token_label)
            with token.open(user_pin=self._pin) as session:
                key = session.get_key(
                    label=self._key_label,
                    object_class=pkcs11.ObjectClass.PRIVATE_KEY,
                    key_type=pkcs11.KeyType.RSA,
                )
                signature = bytes(
                    key.sign(
                        manifest_bytes,
                        mechanism=pkcs11.Mechanism.SHA256_RSA_PKCS,
                    )
                )
            self._public_key.verify(
                signature,
                manifest_bytes,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except PrivacyGraphError:
            raise
        except (pkcs11.PKCS11Error, OSError, ValueError, TypeError, RuntimeError) as error:
            raise PrivacyGraphError(
                "PKCS#11 manifest signing failed or HSM certificate/key did not match"
            ) from error
        return signature


def verify_signed_manifest(
    *,
    manifest_path: Path,
    signature_path: Path,
    ciphertext_path: Path,
    certificate_path: Path,
) -> dict[str, Any]:
    try:
        from cryptography import x509
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
    except ImportError as error:
        raise PrivacyGraphError(
            "Signature verification requires the cryptography package"
        ) from error
    manifest_bytes = _read_limited(manifest_path, "Signed graph manifest")
    signature = _read_limited(signature_path, "HSM signature", maximum=1024 * 1024)
    ciphertext = _read_limited(
        ciphertext_path, "FHE aggregate ciphertext", maximum=64 * 1024 * 1024
    )
    certificate_data = _read_limited(
        certificate_path, "HSM signer certificate", maximum=1024 * 1024
    )
    try:
        manifest = json.loads(manifest_bytes)
        if (
            not isinstance(manifest, dict)
            or json.dumps(
                manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
            != manifest_bytes
        ):
            raise PrivacyGraphError("Graph manifest must use canonical JSON encoding")
        try:
            certificate = x509.load_pem_x509_certificate(certificate_data)
        except ValueError:
            certificate = x509.load_der_x509_certificate(certificate_data)
        public_key = certificate.public_key()
        if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 2048:
            raise PrivacyGraphError("HSM certificate must contain an RSA key of at least 2048 bits")
        expected_fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
        if manifest.get("signer_certificate_sha256") != expected_fingerprint:
            raise PrivacyGraphError("Manifest signer certificate fingerprint does not match")
        ciphertext_digest = hashlib.sha256(ciphertext).hexdigest()
        if manifest.get("fhe_aggregate_ciphertext_sha256") != ciphertext_digest:
            raise PrivacyGraphError(
                "FHE aggregate ciphertext digest does not match the signed manifest"
            )
        public_key.verify(signature, manifest_bytes, padding.PKCS1v15(), hashes.SHA256())
    except PrivacyGraphError:
        raise
    except (InvalidSignature, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise PrivacyGraphError("Graph manifest signature verification failed") from error
    return {
        "status": "HSM_SIGNATURE_VERIFIED",
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "signer_certificate_sha256": expected_fingerprint,
        "fhe_aggregate_ciphertext_sha256": ciphertext_digest,
        "limitations": (
            "The signature authenticates these manifest bytes under the supplied "
            "certificate. It does not validate graph truth, HSM trust-chain status, "
            "FHE inputs, or regulatory compliance."
        ),
    }


def create_private_graph_bundle(
    *,
    graph_path: Path,
    scores_path: Path,
    case_id: str,
    public_key_path: Path,
    parameters_path: Path,
    output_directory: Path,
    graph_store: ApacheAGEGraphStore,
    signer: PKCS11ManifestSigner,
    fhe_backend: FHEAcceleratorBackend | None = None,
) -> dict[str, Any]:
    graph_bytes, graph_value = _read_json(graph_path, "Graph JSON")
    _, score_value = _read_json(scores_path, "Private score JSON", maximum=4 * 1024 * 1024)
    nodes, edges = _validate_graph(graph_value, case_id)
    scores = _validate_scores(score_value, nodes)
    if graph_path.resolve() == output_directory.resolve() or output_directory.exists():
        raise PrivacyGraphError("Bundle output directory must be a new, separate path")
    if not output_directory.parent.is_dir():
        raise PrivacyGraphError("Bundle output parent directory must already exist")

    encrypted_scores, aggregate_ciphertext, fhe_metadata = _encrypt_scores(
        public_key_path=public_key_path,
        parameters_path=parameters_path,
        scores=scores,
        accelerator_backend=fhe_backend,
    )
    manifest: dict[str, Any] = {
        "report_type": "SANCTUM_PRIVATE_GRAPH_AGGREGATE",
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "case_id": case_id,
        "graph_backend": "apache-age",
        "graph_name": graph_store._graph_name,
        "graph_input_sha256": hashlib.sha256(graph_bytes).hexdigest(),
        "graph_nodes": len(nodes),
        "graph_edges": len(edges),
        "fhe_scheme": "Microsoft SEAL BFV",
        "fhe_parameters": fhe_metadata,
        "fhe_score_count": len(scores),
        "fhe_score_bounds": {"minimum": 0, "maximum": _MAX_SCORE},
        "fhe_aggregate_ciphertext_sha256": hashlib.sha256(
            aggregate_ciphertext
        ).hexdigest(),
        "hsm_signature_algorithm": "CKM_SHA256_RSA_PKCS",
        "limitations": [
            "The score values remain encrypted in the graph backend and bundle; the client-held secret key is required to decrypt the aggregate.",
            "The HSM signs the manifest only. It does not hold the FHE key or validate graph data or score meaning.",
            "This homomorphic sum is arithmetic over caller-supplied integer scores; it is not a risk verdict or regulatory assessment.",
            "Graph provenance is operator-supplied and is not independently verified by this import.",
        ],
        "signer_certificate_sha256": signer.certificate_fingerprint,
    }
    canonical_manifest = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    signature = signer.sign_manifest(canonical_manifest)
    certificate_fingerprint = signer.certificate_fingerprint
    manifest_id = hashlib.sha256(canonical_manifest).hexdigest()

    try:
        counts = graph_store.import_graph(
            case_id=case_id,
            manifest_id=manifest_id,
            nodes=nodes,
            edges=edges,
            encrypted_scores={
                node_id: ciphertext for node_id, ciphertext in encrypted_scores
            },
        )
    except PrivacyGraphError:
        raise

    stage_directory: Path | None = None
    try:
        stage_directory = Path(
            tempfile.mkdtemp(
                prefix=f".{output_directory.name}.",
                dir=output_directory.parent,
            )
        )
        (stage_directory / "aggregate.seal").write_bytes(aggregate_ciphertext)
        (stage_directory / "manifest.json").write_bytes(canonical_manifest)
        (stage_directory / "manifest.sig").write_bytes(signature)
        os.replace(stage_directory, output_directory)
        stage_directory = None
    except OSError as error:
        raise PrivacyGraphError(
            "Graph was imported, but the signed local bundle could not be published; "
            f"retry with a new output directory (manifest {manifest_id})"
        ) from error
    finally:
        if stage_directory is not None:
            for child in stage_directory.iterdir():
                child.unlink(missing_ok=True)
            stage_directory.rmdir()

    return {
        "status": "PRIVATE_GRAPH_IMPORTED",
        "manifest_id": manifest_id,
        "graph_nodes": counts["nodes_persisted"],
        "graph_edges": counts["edges_persisted"],
        "fhe_score_count": len(scores),
        "aggregate_ciphertext": str(output_directory / "aggregate.seal"),
        "signed_manifest": str(output_directory / "manifest.json"),
        "signature": str(output_directory / "manifest.sig"),
        "signer_certificate_sha256": certificate_fingerprint,
        "fhe_key_custody": "CLIENT_HELD_NOT_STORED_IN_PKCS11",
        "limitations": manifest["limitations"],
    }
