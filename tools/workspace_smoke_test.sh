#!/usr/bin/env bash
set -eu

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ ! -d "$repo_root/security" ]; then
  echo "missing security directory" >&2
  exit 1
fi
if [ ! -f "$repo_root/BUILD.bazel" ]; then
  echo "missing BUILD.bazel" >&2
  exit 1
fi
if [ ! -f "$repo_root/flake.nix" ]; then
  echo "missing flake.nix" >&2
  exit 1
fi

echo "workspace smoke test passed"
