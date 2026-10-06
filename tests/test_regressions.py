import io
import json
import os
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

from banco_agil.adapters.exchange import AwesomeExchange
from banco_agil.adapters.gemini import GeminiInterpreter
from banco_agil.adapters.local_intent import LocalInterpreter
from banco_agil.bootstrap import build_engine
from banco_agil.domain import DomainError, InfrastructureError, Intent
from banco_agil.intent_policy import wants_end
from banco_agil.privacy import display_message, redact_sensitive
from banco_agil.session import Session


def gemini_payload(result=None):
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": json.dumps(result or {"intent": "limit", "currency": "USD"})}
                    ]
                }
            }
        ],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 2},
    }


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.env = patch.dict(
            os.environ,
            {
                "BANCO_LLM_MODE": "demo",
                "BANCO_FX_MODE": "demo",
                "BANCO_MAX_LLM_CALLS_PER_SESSION": "20",
                "BANCO_MAX_LLM_CALLS_PER_ENGINE": "200",
                "BANCO_SESSION_IDLE_SECONDS": "900",
            },
        )
        self.env.start()
        self.engine = build_engine(self.directory)
        self.session = self.login()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def login(self):
        s = Session()
        self.engine.respond(s, "00000000001")
        self.engine.respond(s, "01/01/1990")
        return s

    def say(self, text, event=None):
        return self.engine.respond(self.session, text, event)

    def gemini(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake", "GEMINI_MODEL": "test"}):
            return GeminiInterpreter()

    def test_closure_honors_negation_and_task_scope(self):
        for text in [
            "quero parar o atendimento",
            "quero sair",
            "encerre o atendimento",
            "quero encerrar",
            "cancelar atendimento",
            "por favor finalizar",
        ]:
            with self.subTest(text=text):
                self.assertTrue(wants_end(text))
        for text in [
            "não quero encerrar, quero consultar meu limite",
            "não quero encerrar",
            "pode encerrar a consulta de câmbio e mostrar meu limite",
            "cancelar tarefa",
        ]:
            with self.subTest(text=text):
                self.assertFalse(wants_end(text))
        self.assertIn("1.000,00", self.say("não quero encerrar, quero consultar meu limite"))
        self.assertEqual(self.session.stage, "menu")

    def test_conflicting_event_cannot_close(self):
        self.say("limite", "same")
        self.assertIn("outro conteúdo", self.say("encerrar", "same"))
        self.assertEqual(self.session.stage, "menu")

    def test_income_mention_does_not_start_interview(self):
        self.say("quero aumentar meu limite porque minha renda aumentou")
        self.assertEqual(self.session.stage, "amount")

    def test_negated_interview_does_not_override_limit(self):
        self.assertIn("1.000,00", self.say("não quero atualizar meu score, só consultar o limite"))

    def test_conflicting_actions_require_clarification(self):
        self.assertIn(
            "uma solicitação por vez", self.say("quero aumentar limite e atualizar score")
        )
        self.assertEqual(self.session.stage, "menu")

    def test_unsupported_currency_never_calls_provider(self):
        with patch.object(self.engine.exchange, "quote") as provider:
            for text in [
                "cotação de CAD",
                "cotação do dólar canadense",
                "cotação do iene",
                "cotação de XYZ",
                "cotação de bitcoin",
            ]:
                with self.subTest(text=text):
                    self.assertIn("não suportada", self.say(text))
            provider.assert_not_called()

    def test_multiple_currencies_are_not_silently_reduced(self):
        with patch.object(self.engine.exchange, "quote") as provider:
            self.assertIn("primeiro", self.say("quanto vale euro e dólar?"))
            provider.assert_not_called()
        self.assertIn("EUR", self.say("euro"))

    def test_generic_quote_is_supported(self):
        self.assertEqual(LocalInterpreter().interpret("cotação por favor"), Intent("exchange"))
        self.assertIn("USD", self.say("cotação por favor"))

    def test_explicit_currency_overrides_wrong_model_currency(self):
        with patch.object(
            self.engine.interpreter, "interpret", return_value=Intent("exchange", "EUR")
        ):
            self.assertIn("1 USD", self.say("cotação do dólar"))

    def test_cancel_task_preserves_authentication_and_registered_request(self):
        self.say("aumentar")
        self.say("10000")
        self.say("sim")
        self.say("5000")
        self.assertIn("cancelada", self.say("cancelar tarefa"))
        self.assertEqual(self.session.stage, "menu")
        self.assertEqual(self.session.interview, {})
        self.assertIsNone(self.session.desired_limit)
        self.assertIn("1.000,00", self.say("limite"))
        self.assertIn("rejeitado", (self.directory / "solicitacoes_aumento_limite.csv").read_text())

    def test_expired_session_cannot_replay_personal_response(self):
        self.say("limite", "cached")
        self.session.last_activity = time.monotonic() - 901
        self.assertIn("expirou", self.say("limite", "cached"))
        self.assertEqual(self.session.stage, "closed")
        self.assertEqual(self.session.responses, {})

    def test_expiry_also_protects_direct_service_access(self):
        self.session.last_activity = time.monotonic() - 901
        with self.assertRaises(DomainError):
            self.engine.service.limit(self.session)

    def test_external_calls_are_limited_across_sessions(self):
        adapter = self.gemini()
        self.engine.interpreter = adapter
        self.engine.max_session_calls = 1
        self.engine.max_engine_calls = 2
        with patch.object(
            adapter, "interpret", return_value=Intent("limit", input_tokens=10)
        ) as http:
            self.say("limite")
            self.assertIn("limite de consultas", self.say("limite"))
            other = self.login()
            self.engine.respond(other, "limite")
            third = self.login()
            self.assertIn("deste ambiente", self.engine.respond(third, "limite"))
            self.assertEqual(http.call_count, 2)
        self.assertEqual(self.engine.metrics_snapshot()["llm_input_tokens"], 20)

    def test_concurrent_sessions_cannot_exceed_shared_engine_call_limit(self):
        sessions = [self.login() for _ in range(8)]
        adapter = self.gemini()
        self.engine.interpreter = adapter
        self.engine.max_engine_calls = 3
        with patch.object(adapter, "interpret", return_value=Intent("limit")) as http:
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda s: self.engine.respond(s, "limite"), sessions))
            self.assertEqual(http.call_count, 3)

    def test_provider_failure_consumes_call_limit_and_unknown_usage(self):
        adapter = self.gemini()
        self.engine.interpreter = adapter
        self.engine.max_session_calls = 1
        with patch.object(adapter, "interpret", side_effect=InfrastructureError("offline")) as http:
            self.assertIn("tente novamente", self.say("limite", "retry"))
            self.assertIn("limite de consultas", self.say("limite", "retry"))
            http.assert_called_once()
        self.assertEqual(self.engine.metrics_snapshot()["llm_failures_without_usage"], 1)
        self.assertIn("encerrado", self.say("encerrar"))

    def test_sensitive_formats_removed_before_model_request(self):
        text = "CPF 000 000 000 01, nascimento 01/01/1990, ana@example.com, renda 5000, R$ 900"
        with patch(
            "banco_agil.adapters.gemini.urlopen",
            return_value=io.BytesIO(json.dumps(gemini_payload()).encode()),
        ) as http:
            self.gemini().interpret(text)
        body = http.call_args.args[0].data.decode()
        for sensitive in ["000 000 000 01", "01/01/1990", "ana@example.com", "5000", "900"]:
            self.assertNotIn(sensitive, body)
        for cpf in ["00000000001", "000.000.000-01", "000 000 000 01"]:
            self.assertEqual(redact_sensitive(cpf), "[CPF removido]")

    def test_auth_and_financial_inputs_are_masked_in_ui_history(self):
        self.assertNotIn("00000000001", display_message("00000000001", "cpf"))
        self.assertNotIn("01/01/1990", display_message("01/01/1990", "birth"))
        self.assertNotIn("5000", display_message("5000", "income"))

    def test_compact_birth_is_removed_in_menu_and_model_input(self):
        text = "Nasci em 15071991 e quero consultar meu limite"
        self.assertNotIn("15071991", display_message(text, "menu"))
        with patch(
            "banco_agil.adapters.gemini.urlopen",
            return_value=io.BytesIO(json.dumps(gemini_payload()).encode()),
        ) as http:
            self.gemini().interpret(text)
        self.assertNotIn("15071991", http.call_args.args[0].data.decode())

    def test_malformed_gemini_structures_are_controlled(self):
        malformed = [
            None,
            [],
            {"candidates": None},
            {"candidates": [None]},
            {"candidates": [{"content": {"parts": [None]}}]},
            {"candidates": [{"content": {"parts": [{"text": 123}]}}]},
            gemini_payload({"intent": ["limit"], "currency": "USD"}),
        ]
        no_usage = gemini_payload()
        no_usage["usageMetadata"] = None
        malformed.append(no_usage)
        adapter = self.gemini()
        for payload in malformed:
            with (
                self.subTest(payload=payload),
                patch(
                    "banco_agil.adapters.gemini.urlopen",
                    return_value=io.BytesIO(json.dumps(payload).encode()),
                ),
                self.assertRaises(InfrastructureError),
            ):
                adapter.interpret("limite")

    def test_incomplete_gemini_output_is_not_accepted(self):
        payload = gemini_payload()
        payload["candidates"][0]["finishReason"] = "MAX_TOKENS"
        with (
            patch(
                "banco_agil.adapters.gemini.urlopen",
                return_value=io.BytesIO(json.dumps(payload).encode()),
            ),
            self.assertRaises(InfrastructureError),
        ):
            self.gemini().interpret("limite")

    def test_missing_usage_is_unknown_and_thinking_tokens_are_counted(self):
        payload = gemini_payload()
        payload.pop("usageMetadata")
        with patch(
            "banco_agil.adapters.gemini.urlopen",
            return_value=io.BytesIO(json.dumps(payload).encode()),
        ):
            self.assertFalse(self.gemini().interpret("limite").usage_known)
        payload["usageMetadata"] = {
            "promptTokenCount": 10,
            "candidatesTokenCount": 2,
            "thoughtsTokenCount": 7,
        }
        with patch(
            "banco_agil.adapters.gemini.urlopen",
            return_value=io.BytesIO(json.dumps(payload).encode()),
        ):
            self.assertEqual(self.gemini().interpret("limite").output_tokens, 9)

    def test_malformed_quote_is_controlled(self):
        for payload in [
            None,
            [],
            {"USDBRL": None},
            {"USDBRL": {"bid": None}},
            {"USDBRL": {"bid": "NaN", "timestamp": "0"}},
        ]:
            with (
                self.subTest(payload=payload),
                patch(
                    "banco_agil.adapters.exchange.urlopen",
                    return_value=io.BytesIO(json.dumps(payload).encode()),
                ),
                self.assertRaises(InfrastructureError),
            ):
                AwesomeExchange().quote("USD")

    def test_quote_cache_avoids_external_call(self):
        quote = {"USDBRL": {"bid": "5.1234", "timestamp": str(int(time.time()))}}
        provider = AwesomeExchange()
        with patch(
            "banco_agil.adapters.exchange.urlopen",
            return_value=io.BytesIO(json.dumps(quote).encode()),
        ) as http:
            first = provider.quote("USD")
            self.assertEqual(first, provider.quote("USD"))
            http.assert_called_once()
        self.assertEqual(provider.metrics["cache_hits"], 1)

    def test_quote_rejects_old_reference(self):
        quote = {"USDBRL": {"bid": "5", "timestamp": str(int(time.time()) - 259201)}}
        with (
            patch(
                "banco_agil.adapters.exchange.urlopen",
                return_value=io.BytesIO(json.dumps(quote).encode()),
            ),
            self.assertRaises(InfrastructureError),
        ):
            AwesomeExchange().quote("USD")

    def test_slow_currency_does_not_block_other_currency(self):
        started, release = threading.Event(), threading.Event()
        provider = AwesomeExchange()

        def http(url, timeout):
            currency = "USD" if "USD-BRL" in url else "EUR"
            if currency == "USD":
                started.set()
                if not release.wait(2):
                    raise OSError("timeout")
            return io.BytesIO(
                json.dumps(
                    {
                        f"{currency}BRL": {
                            "bid": "5",
                            "timestamp": str(int(datetime.now(timezone.utc).timestamp())),
                        }
                    }
                ).encode()
            )

        with patch("banco_agil.adapters.exchange.urlopen", side_effect=http):
            with ThreadPoolExecutor(max_workers=2) as pool:
                slow = pool.submit(provider.quote, "USD")
                try:
                    self.assertTrue(started.wait(1))
                    fast = pool.submit(provider.quote, "EUR")
                    self.assertEqual(fast.result(timeout=1).currency, "EUR")
                finally:
                    release.set()
                self.assertEqual(slow.result(timeout=1).currency, "USD")

    def test_reanalysis_retry_preserves_score_and_does_not_duplicate(self):
        self.say("aumentar")
        self.say("10000")
        self.say("sim")
        for text in ["20000", "formal", "1000", "0"]:
            self.say(text)
        repo = self.engine.service.repository
        with patch.object(repo, "request_credit", side_effect=InfrastructureError("disk")):
            self.assertIn("tente novamente", self.say("não", "review"))
        self.assertEqual(repo.client("00000000001").score, 1000)
        self.assertEqual(self.session.stage, "debts")
        self.assertIn("aprovado", self.say("não", "review"))
        self.say("não", "review")
        rows = (self.directory / "solicitacoes_aumento_limite.csv").read_text().splitlines()
        self.assertEqual(len(rows), 3)

    def test_packaged_seeds_match_public_csv_samples(self):
        root = Path(__file__).resolve().parents[1]
        for name in ["clientes.csv", "score_limite.csv", "solicitacoes_aumento_limite.csv"]:
            self.assertEqual(
                files("banco_agil").joinpath("seeds", name).read_bytes(),
                (root / "data" / name).read_bytes(),
            )

    def test_invalid_financial_csv_never_produces_decision(self):
        tables = [
            "score_min,score_max,limite_maximo\n0,1000,NaN\n",
            "score_min,score_max,limite_maximo\n0,1000,-100\n",
            "score_min,score_max,limite_maximo\n0,500,3000\n400,1000,5000\n",
            "score_min,score_max,limite_maximo\n0,400,3000\n402,1000,5000\n",
            "score_min,score_max,limite_maximo\n0,1000,5000,extra\n",
        ]
        self.say("aumentar")
        for table in tables:
            (self.directory / "score_limite.csv").write_text(table)
            self.assertIn("tente novamente", self.say("2500"))
            self.assertEqual(self.session.stage, "amount")
        self.assertEqual(
            len((self.directory / "solicitacoes_aumento_limite.csv").read_text().splitlines()), 1
        )

    def test_corrupt_client_limit_cannot_be_displayed(self):
        path = self.directory / "clientes.csv"
        path.write_text(path.read_text().replace("1000.00", "NaN"))
        self.assertIn("tente novamente", self.say("limite"))

    def test_nonfinite_session_timeout_is_rejected(self):
        for value in ["NaN", "Infinity", "0", "-1"]:
            with (
                self.subTest(value=value),
                patch.dict(os.environ, {"BANCO_SESSION_IDLE_SECONDS": value}),
                self.assertRaises(ValueError),
            ):
                build_engine(self.directory)

    def test_streamlit_complete_journey_and_controls(self):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            self.skipTest("Extra ui não instalado")
        with patch.dict(os.environ, {"BANCO_DATA_DIR": str(self.directory)}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
            for text in [
                "00000000001",
                "01/01/1990",
                "aumentar",
                "10000",
                "sim",
                "20000",
                "formal",
                "1000",
                "0",
                "não",
                "cotação do euro",
            ]:
                app.chat_input[0].set_value(text).run()
                self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.session_state.bank_session.stage, "menu")
            user_messages = [text for role, text in app.session_state.messages if role == "user"]
            self.assertNotIn("00000000001", user_messages)
            self.assertNotIn("01/01/1990", user_messages)
            next(b for b in app.button if b.label == "Pedir aumento").click().run()
            self.assertEqual(app.session_state.bank_session.stage, "amount")
            next(b for b in app.button if b.label == "Cancelar tarefa").click().run()
            self.assertEqual(app.session_state.bank_session.stage, "menu")
            next(b for b in app.button if b.label == "Encerrar atendimento").click().run()
            self.assertEqual(app.session_state.bank_session.stage, "closed")
            self.assertTrue(app.chat_input[0].disabled)
            self.assertEqual(len(app.session_state.messages), 1)
            self.assertEqual(len(app.exception), 0)
