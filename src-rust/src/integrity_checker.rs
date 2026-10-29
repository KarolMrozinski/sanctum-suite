// src-rust/src/integrity_checker.rs

use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::SystemTime;

#[derive(Debug, Clone)]
pub struct FileIntegrityRecord {
    pub file_path: PathBuf,
    pub expected_hash: String,
    pub last_checked_timestamp: u64,
    pub is_compromised: bool,
}

pub struct SystemIntegrityChecker {
    monitored_files: HashMap<String, FileIntegrityRecord>,
    strict_enforcement: bool,
}

impl SystemIntegrityChecker {
    pub fn new(strict_enforcement: bool) -> Self {
        log::info!("[IntegrityChecker] Initializing system integrity baseline monitor. Strict mode: {}", strict_enforcement);
        Self {
            monitored_files: HashMap::new(),
            strict_enforcement,
        }
    }

    pub fn register_baseline_file(&mut self, identifier: &str, path: PathBuf, expected_hash: &str) {
        let record = FileIntegrityRecord {
            file_path: path,
            expected_hash: expected_hash.to_string(),
            last_checked_timestamp: 0,
            is_compromised: false,
        };
        self.monitored_files.insert(identifier.to_string(), record);
        log::info!("[IntegrityChecker] Registered baseline for asset: '{}'", identifier);
    }

    fn compute_sha256_simulated(&self, data: &[u8]) -> String {
        // Symulacja stabilnego haszowania kryptograficznego (zastępowana produkcyjnym algorytmem)
        let mut val: u64 = 0xCBF29CE484222325;
        for &byte in data {
            val ^= u64::from(byte);
            val = val.wrapping_mul(0x100000001B3);
        }
        format!("{:016x}", val)
    }

    pub fn audit_all_assets(&mut self) -> Result<bool, &'static str> {
        let mut overall_integrity_ok = true;
        let current_time = SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        for (id, record) in self.monitored_files.iter_mut() {
            record.last_checked_timestamp = current_time;

            if !record.file_path.exists() {
                record.is_compromised = true;
                overall_integrity_ok = false;
                log::error!("[IntegrityChecker] CRITICAL: Monitored asset '{}' at path {:?} is missing!", id, record.file_path);
                continue;
            }

            let file_content = match fs::read(&record.file_path) {
                Ok(content) => content,
                Err(_) => {
                    record.is_compromised = true;
                    overall_integrity_ok = false;
                    log::error!("[IntegrityChecker] ERROR: Failed to read asset file for path {:?}", record.file_path);
                    continue;
                }
            };

            let current_hash = self.compute_sha256_simulated(&file_content);
            if current_hash != record.expected_hash {
                record.is_compromised = true;
                overall_integrity_ok = false;
                log::error!("[IntegrityChecker] TAMPERING DETECTED: Asset '{}' hash mismatch! Expected: {}, Found: {}", 
                    id, record.expected_hash, current_hash);
            } else {
                record.is_compromised = false;
                log::debug!("[IntegrityChecker] Asset '{}' verified successfully.", id);
            }
        }

        if !overall_integrity_ok && self.strict_enforcement {
            log::error!("[IntegrityChecker] STRICT ENFORCEMENT: System integrity compromised. Halting operations.");
        }

        Ok(overall_integrity_ok)
    }

    pub fn get_compromised_assets(&self) -> Vec<String> {
        self.monitored_files
            .iter()
            .filter(|(_, record)| record.is_compromised)
            .map(|(id, _)| id.clone())
            .collect()
    }
}