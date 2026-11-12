use sanctum_rust_modules::{
    crypto_vault::CryptoVault,
    integrity_checker::SystemIntegrityChecker,
    packet_parser::DeepPacketInspector,
};
use std::path::PathBuf;

fn main() {
    let mut vault = CryptoVault::new("demo-vault", PathBuf::from("./target/demo-vault"));
    let key = [42u8; 32];
    vault.unlock(&key).expect("vault must unlock");
    vault.store_secret("demo-secret", b"sanctum-demo").expect("secret must store");

    let mut checker = SystemIntegrityChecker::new(true);
    checker.register_baseline_file("demo", PathBuf::from("./Cargo.toml"), "unused");
    let _ = checker.audit_all_assets();

    let inspector = DeepPacketInspector::new(2048, false);
    let frame = [0u8; 24];
    let _ = inspector.inspect_raw_frame(&frame);

    println!("rust-module-demo:ok");
}
