#!/usr/bin/env python3
import hashlib
import pytest
from pathlib import Path

from sanctum_suite.core.secure_asset_loader import SecureAssetLoader
from sanctum_suite.core.ai_model_loader import SecureAIModelManager, SecurityError
from sanctum_suite.core.offline_release_bundler import OfflineReleaseBundler

def test_secure_asset_loader_integrity(tmp_path):
    # Przygotowanie środowiska testowego w folderze tymczasowym
    test_dir = tmp_path / "threat_intel"
    test_file = test_dir / "threat_intel_feed.db"
    
    loader = SecureAssetLoader(test_dir)
    
    # Tworzenie pliku testowego z określoną zawartością
    content = b"enterprise-threat-intelligence-payload-v6"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file.write_bytes(content)
    
    expected_hash = hashlib.sha256(content).hexdigest()
    
    # Weryfikacja powinna zakończyć się sukcesem dla prawidłowego hasha
    assert loader.verify_integrity(test_file, expected_hash) is True
    
    # Weryfikacja powinna odrzucić nieprawidłowy hash
    assert loader.verify_integrity(test_file, "invalidhash") is False

def test_ai_model_loader_security_error(tmp_path):
    models_dir = tmp_path / "models"
    manager = SecureAIModelManager(models_dir)
    
    # Próba załadowania nieistniejącego modelu powinna rzucić SecurityError
    with pytest.raises(SecurityError):
        manager.load_heavy_model("non_existent_model.onnx", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")