#include <stdint.h>
#include <string.h>

typedef struct {
    uint32_t magic_id;
    uint32_t flags;
    uint8_t  node_id;
} sanctum_packet_t;

// Prosta funkcja wypełniająca pakiet
void sanctum_fill_packet(sanctum_packet_t *pkt) {
    if (pkt) {
        pkt->magic_id = 0x53434E54; // "SCNT"
        pkt->flags    = 0x00000003; // Secured & Active
        pkt->node_id  = 0x42;
    }
}

// Funkcja haszująca FNV-1a
uint32_t sanctum_compute_hash(const void *data, uint32_t length) {
    const uint8_t *bytes = (const uint8_t *)data;
    uint32_t hash = 2166136261U;
    for (uint32_t i = 0; i < length; ++i) {
        hash ^= bytes[i];
        hash *= 16777619U;
    }
    return hash;
}

// Funkcja szyfrująca bufor w locie (symetryczna transformacja XOR)
void sanctum_encrypt_buffer(uint8_t *data, uint32_t length, const uint8_t *key, uint32_t key_len) {
    for (uint32_t i = 0; i < length; ++i) {
        data[i] ^= key[i % key_len];
    }
}