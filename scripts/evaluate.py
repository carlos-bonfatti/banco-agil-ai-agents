"""Avaliação de roteamento e custo. Padrão offline; Gemini exige opção explícita."""

import argparse
import json
import math
import platform
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from banco_agil.adapters.local_intent import LocalInterpreter
from banco_agil.domain import InfrastructureError, Intent, normalize
from banco_agil.intent_policy import requested_currency, wants_end
from banco_agil.scope_policy import scope_intent

ROOT = Path(__file__).resolve().parents[1]


def price(value: str) -> Decimal:
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount < 0:
            raise ValueError("invalid price")
        return amount
    except (InvalidOperation, ValueError) as exc:
        raise argparse.ArgumentTypeError("Use uma tarifa finita e não negativa.") from exc


def classify(interpreter, message: str) -> tuple[Intent, bool]:
    if wants_end(message):
        return Intent("end"), False
    if normalize(message).strip(".!? ") in {"cancelar", "cancelar tarefa", "voltar ao menu"}:
        return Intent("cancel"), False
    scope = scope_intent(message)
    if scope is not None:
        return Intent(scope), False
    result = interpreter.interpret(message)
    if result.name == "exchange":
        result = Intent(
            result.name,
            requested_currency(message) or result.currency,
            result.input_tokens,
            result.output_tokens,
            result.usage_known,
        )
    return result, bool(getattr(interpreter, "external", False))


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0
    return round(sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)], 3)


def evaluate(
    interpreter,
    cases: list[dict],
    *,
    max_calls: int = 40,
    input_price: Decimal | None = None,
    output_price: Decimal | None = None,
) -> dict:
    if max_calls < 1:
        raise ValueError("O limite de chamadas deve ser positivo.")
    if (input_price is None) != (output_price is None):
        raise ValueError("Informe as duas tarifas ou nenhuma.")
    external = bool(getattr(interpreter, "external", False))
    rows, latencies = [], []
    calls = input_tokens = output_tokens = usage_unknown = 0
    confusion = defaultdict(lambda: defaultdict(int))
    for case in cases:
        message = case["message"]
        local_command = (
            scope_intent(message) is not None
            or wants_end(message)
            or normalize(message).strip(".!? ")
            in {
                "cancelar",
                "cancelar tarefa",
                "voltar ao menu",
            }
        )
        row = {"id": case["id"], "category": case["category"], "expected": case["intent"]}
        if external and not local_command and calls >= max_calls:
            rows.append({**row, "status": "skipped_call_limit", "correct": False})
            continue
        if external and not local_command:
            calls += 1  # Reserva antes da chamada, inclusive quando falha.
        start = time.perf_counter()
        try:
            result, used_external = classify(interpreter, message)
        except InfrastructureError:
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            usage_unknown += 1
            rows.append(
                {
                    **row,
                    "status": "provider_error",
                    "correct": False,
                    "latency_ms": round(latency, 3),
                }
            )
            continue
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
        correct = result.name == case["intent"] and (
            "currency" not in case or result.currency == case["currency"]
        )
        if used_external:
            input_tokens += result.input_tokens
            output_tokens += result.output_tokens
            usage_unknown += int(not result.usage_known)
        confusion[case["intent"]][result.name] += 1
        rows.append(
            {
                **row,
                "status": "ok",
                "predicted": result.name,
                "currency": result.currency if result.name == "exchange" else None,
                "correct": correct,
                "latency_ms": round(latency, 3),
                "external_call": used_external,
            }
        )
    cost = None
    if not external:
        cost = Decimal(0)
    elif input_price is not None:
        cost = (
            Decimal(input_tokens) * input_price + Decimal(output_tokens) * output_price
        ) / 1_000_000
    categories = {}
    for category in sorted({row["category"] for row in rows}):
        group = [row for row in rows if row["category"] == category]
        categories[category] = {
            "cases": len(group),
            "correct": sum(row["correct"] for row in group),
        }
    return {
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "gemini" if external else "demo",
        "model": getattr(interpreter, "model", "local-keywords"),
        "environment": {"python": platform.python_version(), "platform": platform.system()},
        "scope": "single-turn routing policy; no bank operations, UI, or exchange network",
        "dataset_role": "regression baseline; not independent holdout or production quality estimate",
        "cases": len(rows),
        "correct": sum(row["correct"] for row in rows),
        "exact_match_rate": round(sum(row["correct"] for row in rows) / len(rows), 4)
        if rows
        else 0,
        "provider_errors": sum(row["status"] == "provider_error" for row in rows),
        "skipped": sum(row["status"] == "skipped_call_limit" for row in rows),
        "latency_ms": {
            "p50": round(statistics.median(latencies), 3) if latencies else 0,
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
        },
        "external_calls": calls,
        "max_external_calls": max_calls,
        "tokens": {
            "input": input_tokens,
            "output_including_thoughts": output_tokens,
            "calls_with_unknown_usage": usage_unknown,
        },
        "estimated_model_cost_usd": str(cost) if cost is not None else None,
        "cost_estimate_complete": cost is not None and usage_unknown == 0,
        "pricing": {
            "input_usd_per_million": str(input_price) if input_price is not None else None,
            "output_usd_per_million": str(output_price) if output_price is not None else None,
        },
        "cost_note": "User-supplied flat rates; excludes infrastructure and special billing categories. "
        "When usage is unknown, the estimate covers reported usage only; it is not an invoice.",
        "categories": categories,
        "intent_confusion": dict(confusion),
        "results": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["demo", "gemini"], default="demo")
    parser.add_argument("--dataset", type=Path, default=ROOT / "evaluation/intents.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-calls", type=int, default=40)
    parser.add_argument(
        "--min-exact-match", type=float, help="Gate opcional de regressão, entre 0 e 1"
    )
    parser.add_argument("--input-usd-per-million", type=price)
    parser.add_argument("--output-usd-per-million", type=price)
    parser.add_argument("--pricing-date", help="Data de referência das tarifas informadas")
    parser.add_argument("--pricing-source", help="Fonte das tarifas, sem credenciais")
    args = parser.parse_args()
    if args.max_calls < 1:
        parser.error("--max-calls deve ser positivo")
    if args.min_exact_match is not None and not 0 <= args.min_exact_match <= 1:
        parser.error("--min-exact-match deve estar entre 0 e 1")
    if (args.input_usd_per_million is None) != (args.output_usd_per_million is None):
        parser.error("Informe ambas as tarifas ou nenhuma")
    if args.input_usd_per_million is not None and not (args.pricing_date and args.pricing_source):
        parser.error("Tarifas exigem --pricing-date e --pricing-source")
    cases = json.loads(args.dataset.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        parser.error("Dataset deve ser uma lista não vazia")
    ids = set()
    for case in cases:
        if not isinstance(case, dict) or not {"id", "category", "message", "intent"} <= case.keys():
            parser.error("Caso inválido no dataset")
        if any(not isinstance(case[key], str) for key in ["id", "category", "message", "intent"]):
            parser.error("Campos obrigatórios devem ser strings")
        if case["id"] in ids or not 1 <= len(case["message"]) <= 2000:
            parser.error("IDs devem ser únicos e mensagens devem ter 1 a 2000 caracteres")
        ids.add(case["id"])
    if args.mode == "gemini":
        from banco_agil.adapters.gemini import GeminiInterpreter

        interpreter = GeminiInterpreter()
    else:
        interpreter = LocalInterpreter()
    report = evaluate(
        interpreter,
        cases,
        max_calls=args.max_calls,
        input_price=args.input_usd_per_million,
        output_price=args.output_usd_per_million,
    )
    report["dataset"] = args.dataset.name
    report["pricing"]["reference_date"] = args.pricing_date
    report["pricing"]["source"] = args.pricing_source
    output = args.output or ROOT / "docs" / f"evaluation-{args.mode}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: report[key]
                for key in [
                    "mode",
                    "cases",
                    "correct",
                    "provider_errors",
                    "skipped",
                    "latency_ms",
                    "external_calls",
                    "estimated_model_cost_usd",
                ]
            },
            indent=2,
        )
    )
    print(f"Relatório: {output}")
    if args.min_exact_match is not None and report["exact_match_rate"] < args.min_exact_match:
        raise SystemExit("Taxa de acerto abaixo do mínimo configurado; consulte o relatório.")


if __name__ == "__main__":
    main()
