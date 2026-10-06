"""Carga local com cadastros/pedidos sintéticos e concorrência; nenhuma chamada externa."""

import argparse
import csv
import json
import os
import platform
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from banco_agil.adapters.csv_repository import CLIENT_FIELDS, REQUEST_FIELDS
from banco_agil.bootstrap import build_engine
from banco_agil.session import Session
from scripts.evaluate import percentile


def write_rows(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(size: int, workers: int, samples: int, scenario: str) -> dict:
    with tempfile.TemporaryDirectory() as folder:
        directory = Path(folder)
        with patch.dict(os.environ, {"BANCO_LLM_MODE": "demo", "BANCO_FX_MODE": "demo"}):
            engine = build_engine(directory)
        write_rows(
            directory / "clientes.csv",
            CLIENT_FIELDS,
            (
                {
                    "cpf": f"{index:011d}",
                    "nome": "Cliente sintético",
                    "data_nascimento": "1990-01-01",
                    "limite_credito": "1000.00",
                    "score": "400",
                }
                for index in range(1, size + 1)
            ),
        )
        write_rows(
            directory / "solicitacoes_aumento_limite.csv",
            REQUEST_FIELDS,
            (
                {
                    "request_id": f"seed-{index}",
                    "cpf_cliente": "00000000001",
                    "data_hora_solicitacao": "2026-10-04T00:00:00+00:00",
                    "limite_atual": "1000.00",
                    "novo_limite_solicitado": "2500.00",
                    "status_pedido": "aprovado",
                }
                for index in range(size)
            ),
        )

        def turn(index):
            session = Session()
            cpf = f"{size:011d}"  # Última linha: não mede somente o primeiro cadastro.
            if scenario == "credit_write":
                engine.respond(session, cpf)
                engine.respond(session, "01/01/1990")
                engine.respond(session, "aumentar")
                start = time.perf_counter()
                answer = engine.respond(session, "2500", f"request-{index}")
                success = "aprovada" in answer
            else:
                start = time.perf_counter()
                engine.respond(session, cpf)
                engine.respond(session, "01/01/1990")
                answer = engine.respond(session, "limite")
                success = "1.000,00" in answer
            return (time.perf_counter() - start) * 1000, success

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(turn, range(samples)))
        elapsed = time.perf_counter() - start
        latencies = [latency for latency, _ in results]
        return {
            "scenario": scenario,
            "clients": size,
            "initial_credit_requests": size,
            "workers": workers,
            "samples": samples,
            "successes": sum(success for _, success in results),
            "p50_ms": round(statistics.median(latencies), 3),
            "p95_ms": percentile(latencies, 0.95),
            "p99_ms": percentile(latencies, 0.99),
            "scenario_runs_per_second": round(samples / elapsed, 2),
            "external_llm_calls": engine.metrics_snapshot()["llm_calls"],
            "measurement": "credit_write excludes login; login_and_limit includes authentication. "
            "Throughput includes all scenario preparation and executor work.",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[2, 1000, 10000])
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 4])
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs/performance-demo.json",
    )
    args = parser.parse_args()
    if args.samples < 1 or min(args.sizes) < 1 or min(args.workers) < 1:
        parser.error("Tamanhos, amostras e concorrência devem ser positivos")
    results = [
        run(size, workers, args.samples, scenario)
        for size in args.sizes
        for workers in args.workers
        for scenario in ["login_and_limit", "credit_write"]
    ]
    report = {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.system()},
        "scope": "one process; threads; synthetic local CSV; no UI or network; no production SLA",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Relatório: {args.output}")


if __name__ == "__main__":
    main()
