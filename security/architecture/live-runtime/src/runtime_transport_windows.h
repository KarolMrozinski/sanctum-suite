#pragma once

#include <cstdint>
#include <string>

namespace sanctum {
namespace runtime {

enum class TransportMode {
    NamedPipe,
    HyperV,
    Vsock,
    Unknown,
};

struct RuntimeTransportStatus {
    TransportMode mode;
    bool live_mode;
    bool telemetry_ready;
    std::uint64_t timestamp_unix;
};

RuntimeTransportStatus runtime_transport_status();
std::string describe_transport(TransportMode mode);

}  // namespace runtime
}  // namespace sanctum
