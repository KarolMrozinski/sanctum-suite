import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from pathlib import Path


class SecurityReportSigner:
    """Moduł kryptograficznego podpisywania artefaktów i raportów audytowych (RSA-2048)."""

    def __init__(self, key_dir: str = ".keys") -> None:
        self.key_dir = Path(key_dir)
        self.key_dir.mkdir(exist_ok=True)
        self.private_key_path = self.key_dir / "sanctum_private.pem"
        self.public_key_path = self.key_dir / "sanctum_public.pem"
        self._ensure_keys()

    def _ensure_keys(self) -> None:
        if not self.private_key_path.exists():
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            with open(self.private_key_path, "wb") as f:
                f.write(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )

            public_key = private_key.public_key()
            with open(self.public_key_path, "wb") as f:
                f.write(
                    public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                )

    def sign_file(self, file_path: str) -> str:
        """Podpisuje plik i zwraca sygnaturę Base64."""
        with open(self.private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)

        content = Path(file_path).read_bytes()
        signature = private_key.sign(
            content,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        sig_base64 = base64.b64encode(signature).decode("utf-8")
        
        # Zapis pliku .sig obok raportu
        sig_file = Path(f"{file_path}.sig")
        sig_file.write_text(sig_base64)
        return sig_base64