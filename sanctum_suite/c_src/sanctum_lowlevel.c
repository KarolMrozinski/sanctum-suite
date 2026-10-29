#include <stdint.h>

typedef struct {
    uint32_t magic_id;
    uint32_t flags;
    uint8_t  node_id;
} Sanctum_Packet;

// Funkcja wypełniająca strukturę
void sanctum_fill_packet(Sanctum_Packet* pkt) {
    if (pkt != (void*)0) {
        pkt->magic_id = 0x53414E43; // "SANC"
        pkt->flags    = 0x0000000F;
        pkt->node_id  = 0x42;
    }
}

// Nowa funkcja kryptograficzna / haszująca (FNV-1a) obliczająca sumę kontrolną bufora
uint32_t sanctum_compute_hash(const void* data, uint32_t length) {
    const uint8_t* bytes = (const uint8_t*)data;
    uint32_t hash = 0x811C9DC5; // FNV offset basis
    for (uint32_t i = 0; i < length; i++) {
        hash ^= bytes[i];
        hash *= 0x01000193;     // FNV prime
    }
    return hash;
}