#!/usr/bin/env python3
import os
import hashlib
import urllib.request
from pathlib import Path

# Konfiguracja ścieżek docelowych w strukturze projektu
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "storage" / "heavy_assets"

# Definicja ciężkich komponentów do pobrania (zastąp adresy docelowymi mirrorami)
HEAVY_COMPONENTS = {
    "local_anomaly_model.onnx": {
        "url": "https://internal-artifact-repo.local/models/local_anomaly_model.onnx",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "size_mb": 1250
    },
    "threat_intel_feed.db": {
        "url": "https://internal-artifact-repo.local/db/threat_intel_feed.db",
        "sha256": "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce",
        "size_mb": 1800
    }
}

def verify_checksum(file_path: Path, expected_hash: str) -> bool:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest() == expected_hash

def download_assets():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    for filename, meta in HEAVY_COMPONENTS.items():
        target_path = ASSETS_DIR / filename
        if target_path.exists():
            print(f"[+] Plik {filename} już istnieje. Weryfikacja sumy kontrolnej...")
            if verify_checksum(target_path, meta["sha256"]):
                print(f"[ok] Suma kontrolna dla {filename} jest poprawna.")
                continue
            else:
                print(f"[!] Niepoprawna suma kontrolna. Ponowne pobieranie {filename}...")
        
        print(f"[*] Pobieranie {filename} (szacowany rozmiar: {meta['size_mb']} MB)...")
        urllib.request.urlretrieve(meta["url"], target_path)
        
        if verify_checksum(target_path, meta["sha256"]):
            print(f"[ok] Pobrano i zweryfikowano: {filename}")
        else:
            raise ValueError(f"[!] Błąd krytyczny: Suma kontrolna pobranego pliku {filename} się nie zgadza!")

if __name__ == "__main__":
    download_assets()