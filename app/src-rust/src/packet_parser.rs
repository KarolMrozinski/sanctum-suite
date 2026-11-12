// src-rust/src/packet_parser.rs

use std::net::Ipv4Addr;

#[derive(Debug, Clone, PartialEq)]
pub enum NetworkProtocol {
    TCP = 6,
    UDP = 17,
    ICMP = 1,
    UNKNOWN = 255,
}

impl From<u8> for NetworkProtocol {
    fn from(val: u8) -> Self {
        match val {
            6 => NetworkProtocol::TCP,
            17 => NetworkProtocol::UDP,
            1 => NetworkProtocol::ICMP,
            _ => NetworkProtocol::UNKNOWN,
        }
    }
}

#[derive(Debug, Clone)]
pub struct ParsedPacketMetadata {
    pub source_ip: Ipv4Addr,
    pub dest_ip: Ipv4Addr,
    pub source_port: u16,
    pub dest_port: u16,
    pub protocol: NetworkProtocol,
    pub payload_length: u16,
    pub flags: u8,
    pub anomaly_detected: bool,
    pub inspection_notes: String,
}

pub struct DeepPacketInspector {
    max_allowed_payload: usize,
    strict_air_gap_mode: bool,
}

impl DeepPacketInspector {
    pub fn new(max_allowed_payload: usize, strict_air_gap_mode: bool) -> Self {
        log::info!("[PacketInspector] Initialized. Max payload: {}, Strict Air-Gap: {}", max_allowed_payload, strict_air_gap_mode);
        Self {
            max_allowed_payload,
            strict_air_gap_mode,
        }
    }

    pub fn inspect_raw_frame(&self, raw_bytes: &[u8]) -> Result<ParsedPacketMetadata, &'static str> {
        // Wymóg minimalnego nagłówka IP (20 bajtów) + podstawowe porty (4 bajty) = 24 bajty
        if raw_bytes.len() < 24 {
            return Err("Malformed packet: frame length below minimum threshold (24 bytes)");
        }

        let source_ip = Ipv4Addr::new(raw_bytes[12], raw_bytes[13], raw_bytes[14], raw_bytes[15]);
        let dest_ip = Ipv4Addr::new(raw_bytes[16], raw_bytes[17], raw_bytes[18], raw_bytes[19]);

        let source_port = u16::from_be_bytes([raw_bytes[20], raw_bytes[21]]);
        let dest_port = u16::from_be_bytes([raw_bytes[22], raw_bytes[23]]);

        let protocol_val = raw_bytes[9]; // Protokół w nagłówku IP
        let protocol = NetworkProtocol::from(protocol_val);

        let payload_length = (raw_bytes[4] as u16) << 8 | (raw_bytes[5] as u16);
        let flags = raw_bytes[20]; // Przykładowe wyciągnięcie flag sterujących

        let mut anomaly = false;
        let mut notes = String::from("Packet inspection passed normal checks.");

        // Sprawdzenia restrykcyjne dla środowisk Air-Gapped
        if self.strict_air_gap_mode {
            if !source_ip.is_private() && !source_ip.is_loopback() {
                anomaly = true;
                notes = format!("SECURITY VIOLATION: External source IP {} detected in air-gapped zone", source_ip);
            }
        }

        if (payload_length as usize) > self.max_allowed_payload {
            anomaly = true;
            notes = format!("POSSIBLE BUFFER OVERFLOW: Payload length {} exceeds limit {}", payload_length, self.max_allowed_payload);
        }

        log::debug!("[PacketInspector] Inspected packet src: {}, dest: {}, protocol: {:?}", source_ip, dest_ip, protocol);

        Ok(ParsedPacketMetadata {
            source_ip,
            dest_ip,
            source_port,
            dest_port,
            protocol,
            payload_length,
            flags,
            anomaly_detected: anomaly,
            inspection_notes: notes,
        })
    }

    pub fn validate_tcp_handshake(&self, flags: u8) -> bool {
        // Przykładowa walidacja flag TCP pod kątem skanów portów (np. SYN-FIN)
        let is_syn = (flags & 0x02) != 0;
        let is_fin = (flags & 0x01) != 0;
        
        if is_syn && is_fin {
            log::warn!("[PacketInspector] XMAS / Invalid TCP scan flags detected!");
            return false;
        }
        true
    }
}