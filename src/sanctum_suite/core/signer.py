import base64
import hashlib
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class SecurityReportSigner:
    """Signs reports with a configured production key or a local development key."""

    def __init__(self, key_dir: str = ".keys") -> None:
        environment = os.environ.get("SANCTUM_ENVIRONMENT", "").strip().lower()
        if environment in {"production", "prod", "air-gapped", "air_gapped"}:
            private_key_file = os.environ.get(
                "SANCTUM_REPORT_SIGNING_PRIVATE_KEY_FILE", ""
            ).strip()
            public_key_file = os.environ.get(
                "SANCTUM_REPORT_SIGNING_PUBLIC_KEY_FILE", ""
            ).strip()
            if not private_key_file or not public_key_file:
                raise ValueError(
                    "Production requires explicit report-signing private and public key files"
                )
            self.private_key_path = Path(private_key_file).expanduser()
            self.public_key_path = Path(public_key_file).expanduser()
            self.key_dir = self.private_key_path.parent
            self._validate_key_pair()
            return

        self._private_key: rsa.RSAPrivateKey | None = None
        self.public_key_fingerprint: str | None = None
        self.key_dir = Path(key_dir)
        self.key_dir.mkdir(parents=True, exist_ok=True)
        self.private_key_path = self.key_dir / "sanctum_private.pem"
        self.public_key_path = self.key_dir / "sanctum_public.pem"
        self._ensure_keys()

    def _ensure_keys(self) -> None:
        private_exists = self.private_key_path.is_file()
        public_exists = self.public_key_path.is_file()
        if private_exists != public_exists:
            raise ValueError("Report-signing key pair is incomplete")
        if private_exists:
            if os.name != "nt":
                self.private_key_path.chmod(0o600)
            self._validate_key_pair()
            return

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.private_key_path.write_bytes(private_bytes)
        self.public_key_path.write_bytes(public_bytes)
        if os.name != "nt":
            self.private_key_path.chmod(0o600)
        self._validate_key_pair()

    def _validate_key_pair(self) -> None:
        if not self.private_key_path.is_file() or not self.public_key_path.is_file():
            raise ValueError("Configured report-signing key files must both exist")
        try:
            private_key = serialization.load_pem_private_key(
                self.private_key_path.read_bytes(),
                password=None,
            )
            public_key = serialization.load_pem_public_key(
                self.public_key_path.read_bytes()
            )
        except (OSError, TypeError, ValueError) as error:
            raise ValueError(
                "Report-signing key files must contain readable, unencrypted PEM keys"
            ) from error
        if not isinstance(private_key, rsa.RSAPrivateKey) or not isinstance(
            public_key, rsa.RSAPublicKey
        ):
            raise ValueError("Report-signing keys must use RSA")
        if private_key.key_size < 2048 or public_key.key_size < 2048:
            raise ValueError("Report-signing RSA keys must be at least 2048 bits")
        private_public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        if private_public_bytes != public_bytes:
            raise ValueError("Report-signing public key does not match private key")
        self._private_key = private_key
        self.public_key_fingerprint = hashlib.sha256(public_bytes).hexdigest()

    def sign_bytes(self, content: bytes) -> str:
        private_key = self._private_key
        if private_key is None:
            raise ValueError("Report-signing private key is unavailable")
        signature = private_key.sign(
            content,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("ascii")

    def sign_file(self, file_path: str) -> str:
        """Signs a file and writes its detached Base64 signature beside the file."""
        content = Path(file_path).read_bytes()
        signature_base64 = self.sign_bytes(content)
        Path(f"{file_path}.sig").write_text(signature_base64, encoding="ascii")
        return signature_base64

    @staticmethod
    def verify_bytes(
        content: bytes,
        signature_base64: str,
        public_key_pem: bytes,
    ) -> None:
        try:
            public_key = serialization.load_pem_public_key(public_key_pem)
            signature = base64.b64decode(signature_base64, validate=True)
        except (TypeError, ValueError) as error:
            raise ValueError("Report signature or public-key encoding is invalid") from error
        if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 2048:
            raise ValueError("Report verification requires an RSA public key of at least 2048 bits")
        try:
            public_key.verify(
                signature,
                content,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
        except InvalidSignature as error:
            raise ValueError("Report signature verification failed") from error
