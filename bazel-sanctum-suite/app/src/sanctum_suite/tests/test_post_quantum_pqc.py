import json

import pytest
from typer.testing import CliRunner

from sanctum_suite import main
from sanctum_suite.core.post_quantum_pqc import (
    decrypt_hybrid,
    encrypt_hybrid,
    generate_hybrid_encryption_key_pair,
)


def test_hybrid_ml_kem_and_x25519_envelope_round_trips_and_detects_tampering():
    keys = generate_hybrid_encryption_key_pair()
    plaintext = b"signed audit checkpoint contents"
    envelope = encrypt_hybrid(
        plaintext,
        mlkem_public_key=keys["mlkem_public_key"],
        x25519_public_key=keys["x25519_public_key"],
    )

    assert decrypt_hybrid(
        envelope,
        mlkem_private_key=keys["mlkem_private_key"],
        x25519_private_key=keys["x25519_private_key"],
    ) == plaintext

    document = json.loads(envelope)
    document["ciphertext"] = ("A" if document["ciphertext"][0] != "A" else "B") + (
        document["ciphertext"][1:]
    )
    tampered_envelope = json.dumps(
        document, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    with pytest.raises(ValueError, match="authentication failed"):
        decrypt_hybrid(
            tampered_envelope,
            mlkem_private_key=keys["mlkem_private_key"],
            x25519_private_key=keys["x25519_private_key"],
        )


def test_hybrid_envelope_rejects_a_different_recipient_key_pair():
    recipient = generate_hybrid_encryption_key_pair()
    other = generate_hybrid_encryption_key_pair()
    envelope = encrypt_hybrid(
        b"checkpoint",
        mlkem_public_key=recipient["mlkem_public_key"],
        x25519_public_key=recipient["x25519_public_key"],
    )

    with pytest.raises(ValueError, match="not addressed to these recipient keys"):
        decrypt_hybrid(
            envelope,
            mlkem_private_key=other["mlkem_private_key"],
            x25519_private_key=other["x25519_private_key"],
        )


def test_hybrid_kem_cli_encrypts_and_decrypts_a_checkpoint_file(tmp_path):
    key_directory = tmp_path / "recipient"
    generated = CliRunner().invoke(
        main.app,
        ["pqc-kem-keygen", "--key-directory", str(key_directory)],
    )
    assert generated.exit_code == 0, generated.output

    source_file = tmp_path / "checkpoint.json"
    encrypted_file = tmp_path / "checkpoint.json.hybrid.enc"
    decrypted_file = tmp_path / "checkpoint-restored.json"
    source_file.write_bytes(b"signed checkpoint")
    encrypted = CliRunner().invoke(
        main.app,
        [
            "pqc-encrypt",
            "--input-file",
            str(source_file),
            "--mlkem-public-key-file",
            str(key_directory / "mlkem768-public.bin"),
            "--x25519-public-key-file",
            str(key_directory / "x25519-public.bin"),
            "--output-file",
            str(encrypted_file),
        ],
    )
    assert encrypted.exit_code == 0, encrypted.output

    decrypted = CliRunner().invoke(
        main.app,
        [
            "pqc-decrypt",
            "--input-file",
            str(encrypted_file),
            "--mlkem-private-key-file",
            str(key_directory / "mlkem768-private.bin"),
            "--x25519-private-key-file",
            str(key_directory / "x25519-private.bin"),
            "--output-file",
            str(decrypted_file),
        ],
    )
    assert decrypted.exit_code == 0, decrypted.output
    assert decrypted_file.read_bytes() == source_file.read_bytes()
