#!/usr/bin/env python3

import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (SecureAIModelManager): %(message)s"
)
logger = logging.getLogger("SecureAIModelManager")

AI_MODELS_DIR = Path(os.getenv("SANCTUM_AI_MODELS_DIR", "/var/lib/sanctum/models"))

class ModelSecurityError(Exception):
    pass

SecurityError = ModelSecurityError

class SecureAIModelManager:

    def __init__(self, models_dir: Path = AI_MODELS_DIR):
        self.models_dir = Path(models_dir)
        self._loaded_models: Dict[str, Any] = {}
        self.models_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inicjalizacja SecureAIModelManager w katalogu: {self.models_dir}")

    def verify_model_integrity(self, model_filename: str, expected_sha256: str) -> Path:
        model_path = self.models_dir / model_filename
        if not model_path.exists():
            raise SecurityError(f"Model AI nie został odnaleziony w ścieżce systemowej: {model_path}")

        logger.info(f"Weryfikacja kryptograficzna modelu ONNX: {model_filename}")
        
        sha256_hash = hashlib.sha256()
        try:
            with open(model_path, "rb") as f:
                for byte_block in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(byte_block)
            calculated_hash = sha256_hash.hexdigest()

            if calculated_hash.lower() != expected_sha256.lower():
                raise SecurityError(
                    f"Krytyczny błąd: Naruszenie nienaruszalności modelu AI {model_filename}! "
                    f"Oczekiwano: {expected_sha256}, Otrzymano: {calculated_hash}"
                )

            logger.info(f"Model {model_filename} zweryfikowany pomyślnie (SHA-256 ok).")
            return model_path

        except Exception as e:
            logger.error(f"Błąd podczas weryfikacji sumy kontrolnej modelu: {e}")
            raise SecurityError(f"Weryfikacja modelu nie powiodła się: {e}") from e

    def load_heavy_model(self, model_filename: str, expected_sha256: str) -> Dict[str, Any]:
        try:
            model_path = self.verify_model_integrity(model_filename, expected_sha256)
        except SecurityError:
            raise
        
        if model_filename in self._loaded_models:
            logger.debug(f"Model {model_filename} jest już załadowany w pamięci.")
            return self._loaded_models[model_filename]

        logger.info(f"Ładowanie ciężkiego modelu AI do przestrzeni pamięci roboczej: {model_filename}")
        
        try:
            model_size_mb = model_path.stat().st_size / (1024 * 1024)
            
            model_context = {
                "filename": model_filename,
                "path": str(model_path),
                "size_mb": round(model_size_mb, 2),
                "loaded_at": datetime.utcnow().isoformat() + "Z",
                "status": "active_in_memory"
            }
            
            self._loaded_models[model_filename] = model_context
            logger.info(f"Model {model_filename} ({model_context['size_mb']} MB) załadowany pomyślnie.")
            return model_context

        except Exception as e:
            logger.error(f"Błąd inicjalizacji kontekstu modelu AI: {e}")
            raise ModelSecurityError(f"Nie udało się załadować modelu AI: {e}") from e

    def unload_model(self, model_filename: str) -> bool:
        if model_filename in self._loaded_models:
            del self._loaded_models[model_filename]
            logger.info(f"Wyczyszczono model {model_filename} z pamięci roboczej.")
            return True
        return False