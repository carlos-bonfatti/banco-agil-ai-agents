import unittest
from decimal import Decimal
from unittest.mock import Mock

from banco_agil.adapters.local_intent import LocalInterpreter
from banco_agil.domain import InfrastructureError, Intent
from scripts.evaluate import evaluate, price


class EvaluationTests(unittest.TestCase):
    def test_demo_has_no_external_cost(self):
        report = evaluate(
            LocalInterpreter(),
            [
                {
                    "id": "1",
                    "category": "limit",
                    "message": "limite",
                    "intent": "limit",
                }
            ],
        )
        self.assertEqual(report["correct"], 1)
        self.assertEqual(report["external_calls"], 0)
        self.assertEqual(report["estimated_model_cost_usd"], "0")

    def test_call_limit_does_not_block_local_closure(self):
        adapter = Mock(external=True, model="fake")
        adapter.interpret.return_value = Intent("limit", input_tokens=100, output_tokens=10)
        cases = [
            {"id": "1", "category": "limit", "message": "limite", "intent": "limit"},
            {"id": "2", "category": "limit", "message": "limite", "intent": "limit"},
            {"id": "3", "category": "closure", "message": "encerrar", "intent": "end"},
        ]
        report = evaluate(
            adapter, cases, max_calls=1, input_price=Decimal("1"), output_price=Decimal("2")
        )
        adapter.interpret.assert_called_once()
        self.assertEqual(report["skipped"], 1)
        self.assertEqual(report["correct"], 2)
        self.assertEqual(Decimal(report["estimated_model_cost_usd"]), Decimal("0.00012"))
        self.assertTrue(report["cost_estimate_complete"])

    def test_failure_is_not_reported_as_zero_known_cost(self):
        adapter = Mock(external=True, model="fake")
        adapter.interpret.side_effect = InfrastructureError("unavailable")
        report = evaluate(
            adapter,
            [
                {
                    "id": "1",
                    "category": "limit",
                    "message": "limite",
                    "intent": "limit",
                }
            ],
            input_price=Decimal("1"),
            output_price=Decimal("2"),
        )
        self.assertEqual(report["external_calls"], 1)
        self.assertEqual(report["provider_errors"], 1)
        self.assertEqual(report["tokens"]["calls_with_unknown_usage"], 1)
        self.assertFalse(report["cost_estimate_complete"])

    def test_unknown_usage_makes_estimate_incomplete(self):
        adapter = Mock(external=True, model="fake")
        adapter.interpret.return_value = Intent("limit", usage_known=False)
        report = evaluate(
            adapter,
            [
                {
                    "id": "1",
                    "category": "limit",
                    "message": "limite",
                    "intent": "limit",
                }
            ],
            input_price=Decimal("1"),
            output_price=Decimal("2"),
        )
        self.assertFalse(report["cost_estimate_complete"])

    def test_price_rejects_negative_and_nonfinite_values(self):
        import argparse

        for value in ["-1", "NaN", "Infinity", "invalid"]:
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                price(value)
