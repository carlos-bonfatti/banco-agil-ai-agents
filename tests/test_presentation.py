import unittest
from datetime import datetime, timezone

from banco_agil.presentation import BRASILIA, greeting


class PresentationTests(unittest.TestCase):
    def test_greeting_boundaries(self):
        for hour, expected in (
            (0, "Boa noite"),
            (4, "Boa noite"),
            (5, "Bom dia"),
            (11, "Bom dia"),
            (12, "Boa tarde"),
            (17, "Boa tarde"),
            (18, "Boa noite"),
            (23, "Boa noite"),
        ):
            with self.subTest(hour=hour):
                text = greeting(datetime(2026, 10, 4, hour, tzinfo=BRASILIA))
                self.assertTrue(text.startswith(expected))
                self.assertIn("Banco Ágil", text)
                self.assertIn("CPF fictício", text)

    def test_utc_timestamp_is_converted(self):
        self.assertTrue(
            greeting(datetime(2026, 10, 4, 14, tzinfo=timezone.utc)).startswith("Bom dia")
        )
        self.assertTrue(
            greeting(datetime(2026, 10, 5, 1, tzinfo=timezone.utc)).startswith("Boa noite")
        )

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            greeting(datetime(2026, 10, 4, 12))
