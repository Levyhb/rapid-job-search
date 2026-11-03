"""Inicia a API com o ambiente virtual local: py run ou py run.py."""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Iniciar o backend do RapidJobSearch.")
    parser.add_argument("--port", type=int, default=8000, help="Porta da API (padrão: 8000).")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("A porta deve estar entre 1 e 65535.")

    backend = Path(__file__).resolve().parent
    python = backend / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.is_file():
        print(
            "Ambiente virtual não encontrado. Execute scripts/setup.ps1 na raiz do projeto.",
            file=sys.stderr,
        )
        return 1

    try:
        minimum = (backend.parent / ".python-version").read_text(encoding="utf-8").strip()
        probe = subprocess.run(
            [
                str(python), "-I", "-c",
                "import sys; minimum=tuple(map(int,sys.argv[1].split('.'))); "
                "sys.exit(0 if sys.version_info[:2] == (3,14) "
                "and sys.version_info[:3] >= minimum else 1)",
                minimum,
            ],
            cwd=backend,
        )
        if probe.returncode:
            print(f"Atualize o ambiente virtual para Python 3.14 com patch >= {minimum}.",
                  file=sys.stderr)
            return 1
        migration = subprocess.run([str(python), "-m", "alembic", "upgrade", "head"], cwd=backend)
        if migration.returncode:
            print(
                "Não foi possível preparar o banco. Inicie o Docker Desktop e execute "
                "scripts/dev.ps1 infra na raiz do projeto.",
                file=sys.stderr,
            )
            return migration.returncode

        return subprocess.call(
            [
                str(python),
                "-m",
                "uvicorn",
                "app.main:app",
                "--reload",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
            ],
            cwd=backend,
        )
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
