#!/usr/bin/env python3

import os
import tarfile
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (OfflineReleaseBundler): %(message)s"
)
logger = logging.getLogger("OfflineReleaseBundler")

RELEASE_BUNDLE_DIR = Path(os.getenv("SANCTUM_RELEASE_BUNDLE_DIR", "/var/lib/sanctum/bundles"))

class BundlerError(Exception):
    pass

class OfflineReleaseBundler:

    def __init__(self, output_dir: Path = RELEASE_BUNDLE_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inicjalizacja OfflineReleaseBundler z katalogiem wyjściowym: {self.output_dir}")

    def create_release_bundle(self, source_dir: Path, bundle_name: str) -> Dict[str, Any]:
        source_dir = Path(source_dir)
        if not source_dir.exists() or not source_dir.is_dir():
            raise NotADirectoryError(f"Katalog źródłowy paczki nie istnieje lub nie jest katalogiem: {source_dir}")

        tar_filename = f"{bundle_name}.tar.gz"
        tar_path = self.output_dir / tar_filename
        
        logger.info(f"Rozpoczęto pakowanie archiwum offline z {source_dir} -> {tar_path}")

        try:
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(source_dir, arcname=source_dir.name)

            file_size = tar_path.stat().st_size
            file_size_mb = round(file_size / (1024 * 1024), 2)

            sha256_hash = hashlib.sha256()
            with open(tar_path, "rb") as f:
                for byte_block in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(byte_block)
            bundle_hash = sha256_hash.hexdigest()

            manifest = {
                "bundle_name": bundle_name,
                "filename": tar_filename,
                "size_bytes": file_size,
                "size_mb": file_size_mb,
                "sha256": bundle_hash,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }

            manifest_path = self.output_dir / f"{bundle_name}_manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=4, sort_keys=True), encoding="utf-8")

            logger.info(f"Paczka offline {tar_filename} została pomyślnie utworzona i zabezpieczona manifestem.")
            return manifest

        except Exception as e:
            logger.error(f"Błąd podczas tworzenia paczki offline: {e}")
            raise BundlerError(f"Nie udało się utworzyć paczki dystrybucyjnej: {e}") from e

    def unpack_release_bundle(self, bundle_filename: str, target_extraction_dir: Path) -> Path:
        tar_path = self.output_dir / bundle_filename
        if not tar_path.exists():
            raise FileNotFoundError(f"Paczka do rozpakowania nie istnieje: {tar_path}")

        target_extraction_dir = Path(target_extraction_dir)
        target_extraction_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Rozpoczęto bezpieczne rozpakowywanie paczki {bundle_filename} do {target_extraction_dir}")

        try:
            with tarfile.open(tar_path, "r:gz") as tar:
                members = tar.getmembers()
                for member in members:
                    if member.islnk() or member.issym():
                        raise BundlerError(f"Wykryto niebezpieczny link w archiwum: {member.name}")
                    member_path = (target_extraction_dir / member.name).resolve()
                    extraction_root = target_extraction_dir.resolve()
                    if not str(member_path).startswith(str(extraction_root)):
                        raise BundlerError(f"Wykryto próbę Path Traversal w archiwum: {member.name}")

                for member in members:
                    destination = target_extraction_dir / member.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if member.isdir():
                        destination.mkdir(parents=True, exist_ok=True)
                        continue
                    if member.isfile():
                        extracted_file = tar.extractfile(member)
                        if extracted_file is None:
                            raise BundlerError(f"Nie udało się odczytać pliku z archiwum: {member.name}")
                        with extracted_file, open(destination, "wb") as output_stream:
                            output_stream.write(extracted_file.read())
                        continue
                    raise BundlerError(f"Wykryto nieobsługiwany typ wpisu archiwum: {member.name}")

            logger.info(f"Paczka {bundle_filename} została pomyślnie rozpakowana.")
            return target_extraction_dir

        except Exception as e:
            logger.error(f"Błąd podczas rozpakowywania paczki: {e}")
            raise BundlerError(f"Nie udało się rozpakować paczki offline: {e}") from e