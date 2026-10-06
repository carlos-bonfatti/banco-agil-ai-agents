"""Verifica instalação offline e CLI a partir do wheel, fora do checkout."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SMOKE = """
import io
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import banco_agil
assert str(Path(banco_agil.__file__).resolve()).startswith(sys.argv[1])
from banco_agil.cli import main
sys.stdin = io.StringIO(chr(10).join([
    "00000000001", "01/01/1990", "limite", "encerrar", ""
]))
main()
assert (Path.cwd() / "runtime/data/clientes.csv").exists()
print("INSTALLED_WHEEL_SMOKE_OK")
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        parser.error("Informe um arquivo wheel existente")
    with tempfile.TemporaryDirectory(prefix="banco-agil-installed-") as folder:
        target = (Path(folder) / "site").resolve()
        work = Path(folder) / "work"
        work.mkdir()
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-cache-dir",
                "--no-index",
                "--no-deps",
                "--target",
                str(target),
                str(wheel),
            ],
            check=True,
        )
        environment = {
            key: value for key, value in os.environ.items() if not key.startswith("BANCO_")
        }
        result = subprocess.run(
            [sys.executable, "-I", "-c", SMOKE, str(target)],
            cwd=work,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        if "1.000,00" not in result.stdout or "Atendimento encerrado" not in result.stdout:
            raise RuntimeError("A jornada do pacote instalado não concluiu corretamente")
        print(result.stdout)


if __name__ == "__main__":
    main()
