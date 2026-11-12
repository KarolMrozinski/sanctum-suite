// src-rust/src/crypto_vault.rs

use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};
use std::collections::HashMap;

#[derive(Debug)]
pub enum VaultError {
    Locked,
    InvalidTokenLength,
    IoError(std::string::String),
    DecryptionFailed,
    IntegrityViolation,
}

pub struct SecureMemoryBuffer {
    data: Vec<u8>,
}

impl SecureMemoryBuffer {
    pub fn new(size: usize) -> Self {
        Self {
            data: vec![0u8; size],
        }
    }

    pub fn write_data(&mut self, src: &[u8]) -> Result<(), &'static str> {
        if src.len() > self.data.len() {
            return Err("Buffer overflow attempted in SecureMemoryBuffer");
        }
        self.data[..src.len()].copy_from_slice(src);
        Ok(())
    }

    pub fn read_data(&self) -> &[u8] {
        &self.data
    }
}

impl Drop for SecureMemoryBuffer {
    fn drop(&mut self) {
        // Zeroization w trakcje niszczenia struktury w pamięci RAM
        for byte in self.data.iter_mut() {
            *byte = 0;
        }
        log::info!("[CryptoVault-RAM] Secure memory buffer safely wiped and zeroized.");
    }
}

pub struct CryptoVault {
    vault_id: String,
    storage_path: PathBuf,
    is_locked: bool,
    master_key_hash: u64,
    audit_log: Vec<String>,
    metadata_cache: HashMap<String, String>,
}

impl CryptoVault {
    pub fn new(vault_id: &str, storage_path: PathBuf) -> Self {
        log::info!("[CryptoVault] Initializing enterprise vault instance: {}", vault_id);
        Self {
            vault_id: vault_id.to_string(),
            storage_path,
            is_locked: true,
            master_key_hash: 0,
            audit_log: Vec::new(),
            metadata_cache: HashMap::new(),
        }
    }

    pub fn unlock(&mut self, master_token: &[u8]) -> Result<(), VaultError> {
        if master_token.len() < 32 {
            self.log_audit("FAILED_UNLOCK: Token too short");
            return Err(VaultError::InvalidTokenLength);
        }

        // Symulacja obliczenia hasha klucza głównego
        let mut hash: u64 = 5381;
        for &byte in master_token {
            hash = ((hash << 5).wrapping_add(hash)).wrapping_add(u64::from(byte));
        }

        self.master_key_hash = hash;
        self.is_locked = false;
        self.log_audit("SUCCESS_UNLOCK: Vault unlocked successfully");
        log::info!("[CryptoVault] Vault {} successfully unlocked.", self.vault_id);
        Ok(())
    }

    pub fn lock(&mut self) {
        self.is_locked = true;
        self.master_key_hash = 0;
        self.metadata_cache.clear();
        self.log_audit("VAULT_LOCK: Vault securely locked");
        log::info!("[CryptoVault] Vault {} locked and memory cache cleared.", self.vault_id);
    }

    pub fn store_secret(&mut self, key: &str, secret_data: &[u8]) -> Result<(), VaultError> {
        if self.is_locked {
            return Err(VaultError::Locked);
        }

        let mut secure_buf = SecureMemoryBuffer::new(secret_data.len());
        secure_buf.write_data(secret_data).map_err(|e| VaultError::IoError(e.to_string()))?;

        // Zapis do bezpiecznego pliku w strukturze skarbca
        if !self.storage_path.exists() {
            fs::create_dir_all(&self.storage_path).map_err(|e| VaultError::IoError(e.to_string()))?;
        }

        let file_path = self.storage_path.join(format!("{}.sec", key));
        let mut file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(file_path)
            .map_err(|e| VaultError::IoError(e.to_string()))?;

        file.write_all(secure_buf.read_data()).map_err(|e| VaultError::IoError(e.to_string()))?;
        
        self.metadata_cache.insert(key.to_string(), format!("Stored at {}", SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()));
        self.log_audit(&format!("STORE_SECRET: Key '{}' stored successfully", key));
        
        Ok(())
    }

    pub fn retrieve_secret(&self, key: &str) -> Result<Vec<u8>, VaultError> {
        if self.is_locked {
            return Err(VaultError::Locked);
        }

        let file_path = self.storage_path.join(format!("{}.sec", key));
        if !file_path.exists() {
            return Err(VaultError::IoError("Secret not found".to_string()));
        }

        let mut file = fs::File::open(file_path).map_err(|e| VaultError::IoError(e.to_string()))?;
        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer).map_err(|e| VaultError::IoError(e.to_string()))?;

        log::info!("[CryptoVault] Secret '{}' successfully retrieved.", key);
        Ok(buffer)
    }

    fn log_audit(&mut self, message: &str) {
        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();
        let entry = format!("[{}] - {}", timestamp, message);
        self.audit_log.push(entry);
    }

    pub fn get_audit_trail(&self) -> &[String] {
        &self.audit_log
    }
}