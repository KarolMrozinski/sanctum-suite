#include "security/architecture/live-runtime/src/runtime_transport_windows.h"

#include <chrono>
#include <cstdlib>
#include <string>

namespace sanctum {
namespace runtime {

namespace {
TransportMode resolve_transport() {
  const char* env = std::getenv("SANCTUM_VSOCK_MODE");
  if (env != nullptr && std::string(env) == "1") {
    return TransportMode::Vsock;
  }

#if defined(_WIN32)
  return TransportMode::NamedPipe;
#else
  return TransportMode::Vsock;
#endif
}
}  // namespace

RuntimeTransportStatus runtime_transport_status() {
  const auto now = std::chrono::duration_cast<std::chrono::seconds>(
      std::chrono::system_clock::now().time_since_epoch());

  return RuntimeTransportStatus{
      resolve_transport(),
      true,
      true,
      static_cast<std::uint64_t>(now.count()),
  };
}

std::string describe_transport(TransportMode mode) {
  switch (mode) {
    case TransportMode::NamedPipe:
      return "NamedPipe";
    case TransportMode::HyperV:
      return "HyperV";
    case TransportMode::Vsock:
      return "Vsock";
    case TransportMode::Unknown:
    default:
      return "Unknown";
  }
}

}  // namespace runtime
}  // namespace sanctum
