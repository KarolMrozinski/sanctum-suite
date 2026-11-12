import zlib
import struct
from typing import Optional


class LsbSteganographyEngine:
    """Silnik stenografii LSB z nagłówkiem magicznych bajtów i sumą kontrolną CRC32."""

    MAGIC_HEADER = b"CIC3301"

    def hide_payload(self, carrier_bytes: bytearray, payload: bytes) -> bytearray:
        checksum = zlib.crc32(payload)
        header = self.MAGIC_HEADER + struct.pack(">I", len(payload)) + struct.pack(">I", checksum)
        full_data = header + payload

        if len(carrier_bytes) * 8 < len(full_data) * 8:
            raise ValueError("Carrier buffer too small for LSB payload embedding.")

        data_idx = 0
        bit_idx = 0
        for i in range(len(carrier_bytes)):
            if data_idx >= len(full_data):
                break
            byte_val = carrier_bytes[i]
            # Modyfikacja najmniej znaczącego bitu (LSB)
            bit = (full_data[data_idx] >> (7 - bit_idx)) & 1
            carrier_bytes[i] = (byte_val & 0xFE) | bit
            bit_idx += 1
            if bit_idx == 8:
                bit_idx = 0
                data_idx += 1
        return carrier_bytes

    def extract_payload(self, carrier_bytes: bytes) -> Optional[bytes]:
        extracted_bits = []
        for b in carrier_bytes:
            extracted_bits.append(b & 1)

        extracted_bytes = bytearray()
        for i in range(0, len(extracted_bits) - 7, 8):
            byte_val = 0
            for j in range(8):
                byte_val = (byte_val << 1) | extracted_bits[i + j]
            extracted_bytes.append(byte_val)

        if not extracted_bytes.startswith(self.MAGIC_HEADER):
            return None

        header_len = len(self.MAGIC_HEADER)
        if len(extracted_bytes) < header_len + 8:
            return None

        length = struct.unpack(">I", extracted_bytes[header_len:header_len+4])[0]
        expected_checksum = struct.unpack(">I", extracted_bytes[header_len+4:header_len+8])[0]
        
        payload_start = header_len + 8
        if len(extracted_bytes) < payload_start + length:
            return None

        payload = bytes(extracted_bytes[payload_start:payload_start+length])
        if zlib.crc32(payload) != expected_checksum:
            return None # Uszkodzona suma kontrolna

        return payload