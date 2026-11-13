{
  description = "Sanctum Suite layered security and runtime build environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in {
        devShells.default = pkgs.mkShell {
          name = "sanctum-suite-security-shell";

          packages = with pkgs; [
            bash
            git
            gcc
            clang
            llvmPackages.clang
            rustc
            cargo
            cargo-nextest
            wasmtime
            nodejs_20
            npm
            python311
            python311Packages.pip
            protobuf
            bazelisk
            buck2
            nixVersions.latest
            gnat13
            alire
            cmake
            ninja
            pkg-config
            jq
            yq
            opa
            cue
            sqlite
          ];

          shellHook = ''
            export SANCTUM_BUILD_ENV=flake
            export SANCTUM_TOOLCHAIN_VERSION=24.11
            export WASMTIME_HOME="$PWD/.nix-wasm"
            mkdir -p "$WASMTIME_HOME"
            echo "[sanctum] flake environment ready"
          '';
        };
      }
    );
}
