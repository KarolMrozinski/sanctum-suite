#!/usr/bin/env python3

import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (SecureAssetLoader): %(message)s"
)
logger = logging.getLogger("SecureAssetLoader")

SECURE_STORAGE_DIR = Path(os.getenv("SANCTUM_SECURE_STORAGE_DIR", "/var/lib/sanctum"))

class AssetError(Exception):
    pass

class SecureAssetLoader:

    def __init__(self, root_dir: Path = SECURE_STORAGE_DIR):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inicjalizacja SecureAssetLoader z katalogiem głównym: {self.root_dir}")

    def verify_integrity(self, file_path: Path, expected_sha256: str) -> bool:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Plik docelowy nie istnieje: {file_path}")

        logger.info(f"Rozpoczęto weryfikację kryptograficzną zasobu: {file_path.name}")
        
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(byte_block)
            calculated_hash = sha256_hash.hexdigest()

            is_valid = (calculated_hash.lower() == expected_sha256.lower())
            if not is_valid:
                logger.error(
                    f"Naruszenie nienaruszalności zasobu {file_path.name}! "
                    f"Oczekiwano: {expected_sha256}, Otrzymano: {calculated_hash}"
                )
                return False

            logger.info(f"Zasób {file_path.name} zweryfikowany pomyślnie (SHA-256 zgadza się).")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas weryfikacji pliku zasobu: {e}")
            raise AssetError(f"Weryfikacja zasobu nie powiodła się: {e}") from e

    def resolve_asset_path(self, relative_path: str) -> Path:
        resolved = (self.root_dir / relative_path).resolve()
        if not str(resolved).startswith(str(self.root_dir.resolve())):
            raise AssetError(f"Próba wyjścia poza katalog główny systemu (Path Traversal): {relative_path}")
        return resolved

    def get_asset_metadata(self, file_path: Path) -> Dict[str, Any]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Plik nie istnieje: {file_path}")

        stat = file_path.stat()
        size_mb = stat.st_size / (1024 * 1024)

        return {
            "filename": file_path.name,
            "path": str(file_path),
            "size_bytes": stat.st_size,
            "size_mb": round(size_mb, 2),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat() + "Z"
        }