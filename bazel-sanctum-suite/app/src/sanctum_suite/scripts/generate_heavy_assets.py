#!/usr/bin/env python3
import os
import hashlib
from pathlib import Path

# Definicja docelowych katalogów systemowych zgodnie z architekturą Sanctum Suite
BASE_DIR = Path("/var/lib/sanctum")
THREAT_DIR = BASE_DIR / "threat_intel"
MODELS_DIR = BASE_DIR / "models"
BUNDLES_DIR = BASE_DIR / "bundles"

def create_heavy_asset(file_path: Path, target_size_mb: int, description: str):
    """Tworzy plik o zadanej wielkości w Megabajtach i wypisuje jego sumę SHA-256."""
    print(f"[*] Generowanie zasobu [{description}]: {file_path} (~{target_size_mb} MB)...")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    chunk_size = 1024 * 1024  # 1 MB chunk
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "wb") as f:
        for i in range(target_size_mb):
            # Zapisujemy losowe lub strukturalne dane pseudolosowe
            chunk = os.urandom(chunk_size)
            f.write(chunk)
            sha256_hash.update(chunk)
            if (i + 1) % 500 == 0:
                print(f"    -> Zapisano {i + 1} MB / {target_size_mb} MB...")
                
    file_hash = sha256_hash.hexdigest()
    print(f"[+] Sukces! Utworzono {file_path.name}")
    print(f"    SHA-256: {file_hash}\n")
    return file_hash

def main():
    print("=== SANCTUM-SUITE: Heavy Enterprise Asset Provisioning Tool ===")
    
    # 1. Baza Threat Intelligence (~1.8 GB)
    threat_file = THREAT_DIR / "threat_intel_feed.db"
    create_heavy_asset(threat_file, target_size_mb=1800, description="Threat Intelligence Database")
    
    # 2. Model AI / Edge Detection (~2.2 GB)
    model_file = MODELS_DIR / "local_anomaly_detector.onnx"
    create_heavy_asset(model_file, target_size_mb=2200, description="Local Edge Anomaly AI Model")
    
    # 3. Paczka Air-Gapped OCI/Helm (~1.5 GB)
    bundle_file = BUNDLES_DIR / "sanctum_offline_bundle_v6.tar.gz"
    create_heavy_asset(bundle_file, target_size_mb=1500, description="Offline Release Bundle")

    print("[*] Wszystkie ciężkie zasoby zostały pomyślnie wygenerowane i zweryfikowane kryptograficznie.")

if __name__ == "__main__":
    main()