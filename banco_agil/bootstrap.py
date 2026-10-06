import csv
import io
import os
from importlib.resources import files
from pathlib import Path

from banco_agil.adapters.csv_repository import (
    CLIENT_FIELDS,
    REQUEST_FIELDS,
    SCORE_FIELDS,
    CsvRepository,
)
from banco_agil.adapters.exchange import AwesomeExchange, DemoExchange
from banco_agil.adapters.local_intent import LocalInterpreter
from banco_agil.engine import Engine
from banco_agil.service import BankingService


def build_engine(directory: Path | None = None) -> Engine:
    directory = directory or Path(os.getenv("BANCO_DATA_DIR", str(Path.cwd() / "runtime/data")))
    directory.mkdir(parents=True, exist_ok=True)
    repository = CsvRepository(directory)
    # Inicialização protegida pelo mesmo lock usado pelas operações.
    with repository._locked():
        for name in ("clientes.csv", "score_limite.csv", "solicitacoes_aumento_limite.csv"):
            if not (directory / name).exists():
                seed = files("banco_agil").joinpath("seeds", name).read_text(encoding="utf-8")
                fields = {
                    "clientes.csv": CLIENT_FIELDS,
                    "score_limite.csv": SCORE_FIELDS,
                    "solicitacoes_aumento_limite.csv": REQUEST_FIELDS,
                }[name]
                repository._write(name, fields, list(csv.DictReader(io.StringIO(seed))))
    mode = os.getenv("BANCO_LLM_MODE", "demo")
    if mode == "gemini":
        from banco_agil.adapters.gemini import GeminiInterpreter

        interpreter = GeminiInterpreter()
    elif mode == "demo":
        interpreter = LocalInterpreter()
    else:
        raise ValueError("BANCO_LLM_MODE deve ser demo ou gemini.")
    fx_mode = os.getenv("BANCO_FX_MODE", "demo")
    if fx_mode not in {"demo", "live"}:
        raise ValueError("BANCO_FX_MODE deve ser demo ou live.")
    exchange = AwesomeExchange() if fx_mode == "live" else DemoExchange()
    return Engine(
        BankingService(repository),
        interpreter,
        exchange,
        max_session_calls=int(os.getenv("BANCO_MAX_LLM_CALLS_PER_SESSION", "20")),
        max_engine_calls=int(os.getenv("BANCO_MAX_LLM_CALLS_PER_ENGINE", "200")),
        session_timeout=float(os.getenv("BANCO_SESSION_IDLE_SECONDS", "900")),
    )
