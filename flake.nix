{
  description = "Mesh-Agent reproducible development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          pip
          virtualenv
          setuptools
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.git
          ];

          shellHook = ''
            echo "============================================="
            echo "      Mesh-Agent Nix Dev Environment         "
            echo "============================================="
            echo "Python version: $(python --version)"
            echo ""
            if [ ! -d ".venv" ]; then
              echo "Creating virtual environment inside .venv..."
              python -m venv .venv
            fi
            source .venv/bin/activate
            echo "Environment activated. Installing local packages editable..."
            pip install -e ./linerun
            pip install -e .
            echo ""
            echo "Commands:"
            echo "- Run tests: pytest linerun/tests/"
            echo "- Start server: uvicorn app.main:app --reload"
            echo "============================================="
          '';
        };
      });
}
