#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

namespace {

std::filesystem::path find_repo_root(const std::filesystem::path& start) {
    std::filesystem::path current = std::filesystem::weakly_canonical(start);

    for (;;) {
        if (std::filesystem::exists(current / "BUILD.bazel") &&
            std::filesystem::exists(current / "MODULE.bazel") &&
            std::filesystem::exists(current / "security")) {
            return current;
        }

        std::filesystem::path parent = current.parent_path();
        if (parent == current) {
            break;
        }
        current = parent;
    }

    return start;
}

}  // namespace

int main() {
    const std::filesystem::path repo_root = find_repo_root(std::filesystem::current_path());
    const std::filesystem::path security_dir = repo_root / "security";
    const std::filesystem::path build_file = repo_root / "BUILD.bazel";
    const std::filesystem::path flake_file = repo_root / "flake.nix";

    if (!std::filesystem::exists(security_dir) || !std::filesystem::is_directory(security_dir)) {
        std::cerr << "missing security directory under repo root: " << repo_root << std::endl;
        return 1;
    }
    if (!std::filesystem::exists(build_file) || !std::filesystem::is_regular_file(build_file)) {
        std::cerr << "missing BUILD.bazel under repo root: " << repo_root << std::endl;
        return 1;
    }
    if (!std::filesystem::exists(flake_file) || !std::filesystem::is_regular_file(flake_file)) {
        std::cerr << "missing flake.nix under repo root: " << repo_root << std::endl;
        return 1;
    }

    std::cout << "workspace smoke test passed" << std::endl;
    return 0;
}
