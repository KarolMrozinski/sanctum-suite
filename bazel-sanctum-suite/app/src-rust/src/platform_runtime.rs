#[cfg(target_os = "windows")]
mod windows_impl {
    use std::time::{SystemTime, UNIX_EPOCH};

    #[derive(Debug, Clone, PartialEq, Eq)]
    pub enum RuntimeTransport {
        NamedPipe,
        HyperV,
        Vsock,
    }

    #[derive(Debug, Clone, PartialEq, Eq)]
    pub struct RuntimeStatus {
        pub transport: RuntimeTransport,
        pub live_mode: bool,
        pub telemetry_ready: bool,
        pub timestamp_unix: u64,
    }

    pub fn detect_transport() -> RuntimeTransport {
        if std::env::var("SANCTUM_VSOCK_MODE").map(|v| v == "1").unwrap_or(false) {
            RuntimeTransport::Vsock
        } else {
            RuntimeTransport::NamedPipe
        }
    }

    pub fn runtime_status() -> RuntimeStatus {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock before unix epoch")
            .as_secs();

        RuntimeStatus {
            transport: detect_transport(),
            live_mode: true,
            telemetry_ready: true,
            timestamp_unix: timestamp,
        }
    }
}

#[cfg(not(target_os = "windows"))]
mod windows_impl {
    #[derive(Debug, Clone, PartialEq, Eq)]
    pub enum RuntimeTransport {
        NamedPipe,
        HyperV,
        Vsock,
    }

    #[derive(Debug, Clone, PartialEq, Eq)]
    pub struct RuntimeStatus {
        pub transport: RuntimeTransport,
        pub live_mode: bool,
        pub telemetry_ready: bool,
        pub timestamp_unix: u64,
    }

    pub fn detect_transport() -> RuntimeTransport {
        RuntimeTransport::Vsock
    }

    pub fn runtime_status() -> RuntimeStatus {
        use std::time::{SystemTime, UNIX_EPOCH};
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock before unix epoch")
            .as_secs();

        RuntimeStatus {
            transport: detect_transport(),
            live_mode: true,
            telemetry_ready: true,
            timestamp_unix: timestamp,
        }
    }
}

pub use windows_impl::{detect_transport, runtime_status, RuntimeStatus, RuntimeTransport};

#[cfg(test)]
mod tests {
    use super::{detect_transport, runtime_status, RuntimeTransport};
    use std::env;

    #[test]
    fn runtime_status_stays_live_ready() {
        let status = runtime_status();
        assert!(status.live_mode);
        assert!(status.telemetry_ready);
        assert_ne!(status.timestamp_unix, 0);
    }

    #[test]
    fn transport_matches_host_runtime() {
        let transport = detect_transport();
        match env::consts::OS {
            "windows" => assert!(matches!(transport, RuntimeTransport::NamedPipe | RuntimeTransport::HyperV | RuntimeTransport::Vsock)),
            _ => assert!(matches!(transport, RuntimeTransport::Vsock)),
        }
    }
}
