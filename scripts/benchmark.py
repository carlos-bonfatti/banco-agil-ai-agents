"""Microbenchmark local determinístico; não mede LLM, rede ou carga distribuída."""

import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from banco_agil.bootstrap import build_engine
from banco_agil.session import Session

samples = []
with tempfile.TemporaryDirectory() as directory:
    with patch.dict(os.environ, {"BANCO_LLM_MODE": "demo", "BANCO_FX_MODE": "demo"}):
        engine = build_engine(Path(directory))
    for _ in range(300):
        session = Session()
        engine.respond(session, "00000000001")
        engine.respond(session, "01/01/1990")
        start = time.perf_counter()
        engine.respond(session, "qual meu limite?")
        samples.append((time.perf_counter() - start) * 1000)
samples.sort()
print(
    json.dumps(
        {
            "scenario": "authenticated_limit_demo",
            "iterations": len(samples),
            "p50_ms": round(statistics.median(samples), 3),
            "p95_ms": round(samples[int(len(samples) * 0.95) - 1], 3),
            "external_llm_calls": 0,
            "llm_tokens": 0,
            "scope": "single process, temporary local CSV, no network",
        },
        indent=2,
    )
)
