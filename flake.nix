{
  description = "PlanPal student calendar application";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pp = pkgs.python311Packages;

        djangoWithAsserts = pp.buildPythonPackage {
          pname = "django-with-asserts";
          version = "0.0.1";
          src = pkgs.fetchPypi {
            pname = "django-with-asserts";
            version = "0.0.1";
            hash = "sha256-Iz78SNnAOhoFYXs+RyUpa1dbcZnAB7Y62R1pYeCEYvA=";
          };
          doCheck = false;
        };

        pythonEnv = pkgs.python311.withPackages (ps: [
          ps.django
          ps.pillow
          ps.lxml
          ps.coverage
          ps.sqlparse
          ps.cssselect
          ps.django-widget-tweaks
          djangoWithAsserts
        ]);

      in {

        apps.init = {
          type = "app";
          program = toString (pkgs.writeShellScript "init" ''
            set -e
            PROJECT_DIR="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
            cd "$PROJECT_DIR"
            echo "Running migrations..."
            ${pythonEnv}/bin/python manage.py migrate
            echo "Seeding database..."
            ${pythonEnv}/bin/python manage.py seed
            echo ""
            echo "Done. Run the app with: nix run .#run"
          '');
        };

        apps.run = {
          type = "app";
          program = toString (pkgs.writeShellScript "run" ''
            set -e
            PROJECT_DIR="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
            cd "$PROJECT_DIR"
            echo "Starting PlanPal at http://localhost:8000"
            ${pythonEnv}/bin/python manage.py runserver
          '');
        };

        apps.tests = {
          type = "app";
          program = toString (pkgs.writeShellScript "tests" ''
            set -e
            PROJECT_DIR="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
            cd "$PROJECT_DIR"
            echo "Running tests with coverage..."
            ${pythonEnv}/bin/python -m coverage run --source=student_calendar manage.py test student_calendar || true
            ${pythonEnv}/bin/python -m coverage report
            ${pythonEnv}/bin/python -m coverage html -d coverage/
            echo ""
            echo "Coverage report written to ./coverage/index.html"
          '');
        };

        apps.seed = {
          type = "app";
          program = toString (pkgs.writeShellScript "seed" ''
            set -e
            PROJECT_DIR="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
            cd "$PROJECT_DIR"
            echo "Seeding database..."
            ${pythonEnv}/bin/python manage.py seed
            echo "Done."
          '');
        };

        apps.unseed = {
          type = "app";
          program = toString (pkgs.writeShellScript "unseed" ''
            set -e
            PROJECT_DIR="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$PWD")"
            cd "$PROJECT_DIR"
            echo "Unseeding database..."
            ${pythonEnv}/bin/python manage.py unseed
            echo "Done."
          '');
        };

        apps.default = self.apps.${system}.run;

        devShells.default = pkgs.mkShell {
          packages = [ pythonEnv pkgs.git ];
          shellHook = ''
            echo "PlanPal dev environment"
            echo ""
            echo "Available commands:"
            echo "  nix run .#init    — set up, migrate, and seed the database"
            echo "  nix run .#run     — start the development server"
            echo "  nix run .#tests   — run tests and generate coverage report"
            echo "  nix run .#seed    — seed the database"
            echo "  nix run .#unseed  — remove all seed data"
          '';
        };

      });
}
