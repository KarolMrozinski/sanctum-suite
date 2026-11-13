#include "security/architecture/live-runtime/src/runtime_transport_windows.h"

#include <cassert>

int main() {
  const auto status = sanctum::runtime::runtime_transport_status();
  assert(status.live_mode);
  assert(status.telemetry_ready);
  assert(status.timestamp_unix != 0);
  assert(sanctum::runtime::describe_transport(status.mode).size() > 0);
  return 0;
}
