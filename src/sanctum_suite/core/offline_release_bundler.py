#!/usr/bin/env python3
import hashlib
import hmac
from pathlib import Path
import tarfile

# Standardy zarządzania artefaktami wdrożeniowymi w trybie Air-Gapped
RELEASE_BUNDLE_DIR = Path("/var/lib/sanctum/bundles")

class OfflineReleaseBundler:
    def __init__(self, bundle_dir: Path):
        self.bundle_dir = bundle_dir
        self.bundle_dir.mkdir(parents=True, exist_ok=True)

    def verify_bundle_signature(self, bundle_filename: str, expected_sha256: str) -> bool:
        bundle_path = self.bundle_dir / bundle_filename
        if not bundle_path.exists():
            return False
            
        hasher = hashlib.sha256()
        with open(bundle_path, "rb") as f:
            while chunk := f.read(1048576):  # 1MB chunks
                hasher.update(chunk)
        return hmac.compare_digest(hasher.hexdigest(), expected_sha256)

    def unpack_airgap_payload(self, bundle_filename: str, expected_sha256: str, target_unpack_path: Path):
        bundle_path = self.bundle_dir / bundle_filename
        print(f"[*] Weryfikacja kryptograficzna paczki offline: {bundle_filename}")
        
        if not self.verify_bundle_signature(bundle_filename, expected_sha256):
            raise ValueError(f"[!] BŁĄD KRYTYCZNY: Suma kontrolna paczki OCI/Helm {bundle_filename} jest niezgodna!")
            
        print(f"[ok] Paczka {bundle_filename} zweryfikowana. Rozpakowywanie payloadu w trybie Air-Gapped...")
        target_unpack_path.mkdir(parents=True, exist_ok=True)
        
        with tarfile.open(bundle_path, "r:gz") as tar:
            tar.extractall(path=target_unpack_path)
            
        print(f"[ok] Pomyślnie wdrożono artefakty do {target_unpack_path}")

if __name__ == "__main__":
    bundler = OfflineReleaseBundler(RELEASE_BUNDLE_DIR)
    # Przykład użycia dla ciężkiego archiwum kontenerów OCI / wykresów Helm (~1.5 GB)
    # bundler.unpack_airgap_payload("sanctum_offline_bundle_v6.tar.gz", "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce", Path("/opt/sanctum/runtime"))