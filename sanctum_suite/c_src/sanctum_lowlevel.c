#include <stdint.h>

typedef struct {
    uint32_t magic_id;
    uint32_t flags;
    uint8_t  node_id;
} Sanctum_Packet;

// Funkcja z konwencją C, dostępna dla Ady
uint32_t sanctum_get_hardware_status(void) {
    // Tutaj w przyszłości znajdzie się bezpośredni dostęp do sprzętu / API systemu
    return 0x50AA50AA; 
}

// Funkcja wypełniająca strukturę przekazaną z poziomu Ady
void sanctum_fill_packet(Sanctum_Packet* pkt) {
    if (pkt != NULL) {
        pkt->magic_id = 0x53414E43; // "SANC" w hex
        pkt->flags    = 0x0000000F;
        pkt->node_id  = 0x42;
    }
}